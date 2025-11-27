"""
In-memory RDF store using rdflib's Memory store for faster queries.
This provides much faster SPARQL query performance than parsing from file each time.
"""

import os
import gzip
import structlog
from typing import Optional
from rdflib import Graph
from rdflib.plugins.stores.memory import Memory
from pathlib import Path
import hashlib

logger = structlog.get_logger()


class JenaMemoryStore:
    """
    Optimized in-memory RDF store with caching.
    Uses rdflib's Memory store for fast SPARQL queries.
    """
    
    def __init__(self, cache_dir: str = ".jena_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.graph: Optional[Graph] = None
        self.ttl_file = "financial_kg.ttl"
        self.cache_file = self.cache_dir / "financial_kg.ttl.gz"  # Safe format instead of pickle
        
    def _get_file_hash(self, filepath: Path) -> str:
        """Get MD5 hash of file for cache validation."""
        if not filepath.exists():
            return ""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _load_from_cache(self) -> bool:
        """Try to load graph from gzip-compressed turtle cache (safe, no pickle)."""
        try:
            if not self.cache_file.exists():
                return False

            # Check if TTL file has changed
            ttl_path = Path(self.ttl_file)
            if ttl_path.exists():
                current_hash = self._get_file_hash(ttl_path)
                hash_file = self.cache_dir / "financial_kg.hash"

                if hash_file.exists():
                    stored_hash = hash_file.read_text().strip()
                    if current_hash != stored_hash:
                        logger.info("TTL file changed, cache invalidated")
                        return False
                else:
                    return False

            # Load from gzip-compressed turtle (safe - no arbitrary code execution)
            with gzip.open(self.cache_file, 'rt', encoding='utf-8') as f:
                turtle_data = f.read()

            self.graph = Graph(store=Memory())
            self.graph.parse(data=turtle_data, format='turtle')
            logger.info("Loaded RDF graph from cache", triples=len(self.graph))
            return True

        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
            return False
    
    def _save_to_cache(self):
        """Save graph to gzip-compressed turtle cache (safe, no pickle)."""
        try:
            # Serialize to turtle format and compress
            turtle_data = self.graph.serialize(format='turtle')
            with gzip.open(self.cache_file, 'wt', encoding='utf-8') as f:
                f.write(turtle_data)

            # Save TTL file hash
            ttl_path = Path(self.ttl_file)
            if ttl_path.exists():
                current_hash = self._get_file_hash(ttl_path)
                hash_file = self.cache_dir / "financial_kg.hash"
                hash_file.write_text(current_hash)

            logger.info("Saved RDF graph to cache", triples=len(self.graph))

        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")
    
    def get_graph(self) -> Graph:
        """Get or create the in-memory graph."""
        if self.graph is not None:
            return self.graph
        
        # Try to load from cache first
        if self._load_from_cache():
            return self.graph
        
        # Otherwise load from TTL files
        logger.info("Loading RDF graph from TTL files...")
        self.graph = Graph(store=Memory())
        
        # Load ontology
        ontology_path = Path(__file__).parent.parent.parent.parent / "ontologies" / "financial-core.ttl"
        if ontology_path.exists():
            self.graph.parse(ontology_path, format="turtle")
            logger.info("Loaded financial ontology")
        
        # Load data
        if os.path.exists(self.ttl_file):
            self.graph.parse(self.ttl_file, format="turtle")
            logger.info(f"Loaded {len(self.graph)} triples from {self.ttl_file}")
        
        # Save to cache for next time
        self._save_to_cache()
        
        return self.graph
    
    def clear_cache(self):
        """Clear all caches."""
        if self.cache_file.exists():
            self.cache_file.unlink()
        hash_file = self.cache_dir / "financial_kg.hash"
        if hash_file.exists():
            hash_file.unlink()
        self.graph = None
        logger.info("Cleared RDF memory cache")


# Global singleton instance
_memory_store = JenaMemoryStore()


def get_memory_graph() -> Graph:
    """Get the singleton in-memory RDF graph."""
    return _memory_store.get_graph()


def clear_memory_cache():
    """Clear the memory cache (useful after updates)."""
    _memory_store.clear_cache()