"""Business configuration manager for multi-tenant support."""

import os
from typing import Dict, Optional, Any, List
from pathlib import Path
import json
import structlog
from datetime import datetime

from src.core.cache_manager import CacheManager
from src.db.weaviate_client import WeaviateClient
from .models import BusinessConfiguration
from .loaders import ExcelLoader

logger = structlog.get_logger()


class BusinessConfigManager:
    """Manages business configurations for multiple clients/datasets."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None,
                 weaviate_client: Optional[WeaviateClient] = None):
        self.logger = logger.bind(component="config_manager")
        self.cache_manager = cache_manager
        self.weaviate_client = weaviate_client
        self.configs: Dict[str, BusinessConfiguration] = {}
        self.active_config: Optional[BusinessConfiguration] = None
        self.loader = ExcelLoader()
        
        # Default config path - use /tmp for container compatibility
        self.config_dir = Path(os.environ.get("BUSINESS_CONFIG_DIR", "/tmp/configs"))
        try:
            self.config_dir.mkdir(exist_ok=True, parents=True)
        except PermissionError:
            # Fall back to /tmp if default location isn't writable
            self.config_dir = Path("/tmp/configs")
            self.config_dir.mkdir(exist_ok=True, parents=True)
            self.logger.warning(f"Using fallback config directory: {self.config_dir}")
    
    def load_client_config(self, client_id: str, dataset_id: str) -> BusinessConfiguration:
        """Load configuration for a specific client and dataset."""
        config_key = f"{client_id}:{dataset_id}"
        
        # Check cache first
        if self.cache_manager:
            try:
                # Use Redis client directly for generic get/set operations
                cached_config = self.cache_manager.redis_client.get(f"business_config:{config_key}")
                if cached_config:
                    self.logger.info(f"Loaded config from cache for {config_key}")
                    config = BusinessConfiguration(**json.loads(cached_config))
                    self.configs[config_key] = config
                    return config
            except Exception as e:
                self.logger.debug(f"Cache lookup failed: {e}")
        
        # Check if already loaded in memory
        if config_key in self.configs:
            return self.configs[config_key]
        
        # Load from file or create default
        config_file = self.config_dir / f"{client_id}_{dataset_id}.json"
        if config_file.exists():
            self.logger.info(f"Loading config from file: {config_file}")
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                config = BusinessConfiguration(**config_data)
        else:
            # Create default configuration for Arizona Beverages
            if client_id == "arizona_beverages":
                config = self._create_arizona_config(client_id, dataset_id)
            else:
                config = BusinessConfiguration(
                    client_id=client_id,
                    dataset_id=dataset_id,
                    version="1.0.0"
                )
        
        self.configs[config_key] = config
        
        # Cache the configuration
        if self.cache_manager:
            self.cache_manager.set(
                f"business_config:{config_key}",
                config.model_dump_json(),
                ttl=86400  # 24 hours
            )
        
        return config
    
    def _create_arizona_config(self, client_id: str, dataset_id: str) -> BusinessConfiguration:
        """Create Arizona Beverages configuration from Excel files."""
        self.logger.info("Creating Arizona Beverages configuration")
        
        # Load GL mappings
        gl_config = None
        gl_file = "Classified_P_L_Accounts_Arizona Beverages.xls"
        if Path(gl_file).exists():
            gl_config = self.loader.load_gl_mappings(gl_file)
        
        # Load material hierarchy
        material_hierarchy = None
        material_file = "Sales data copy (002).xlsx"
        if Path(material_file).exists():
            material_hierarchy = self.loader.load_material_hierarchy(material_file)
        
        config = BusinessConfiguration(
            client_id=client_id,
            dataset_id=dataset_id,
            version="1.0.0",
            description="Arizona Beverages business configuration",
            gl_mappings=gl_config,
            material_hierarchy=material_hierarchy,
            tags=["beverage", "arizona", "copa"]
        )
        
        # Save configuration
        self.save_config(config)
        
        return config
    
    def save_config(self, config: BusinessConfiguration):
        """Save configuration to file."""
        config_key = f"{config.client_id}:{config.dataset_id}"
        config_file = self.config_dir / f"{config.client_id}_{config.dataset_id}.json"
        
        config.updated_at = datetime.now()
        
        with open(config_file, 'w') as f:
            json.dump(config.model_dump(), f, indent=2, default=str)
        
        self.logger.info(f"Saved config to {config_file}")
        
        # Update cache
        if self.cache_manager:
            self.cache_manager.set(
                f"business_config:{config_key}",
                config.model_dump_json(),
                ttl=86400
            )
    
    def set_active_config(self, client_id: str, dataset_id: str):
        """Set the active configuration."""
        config = self.load_client_config(client_id, dataset_id)
        self.active_config = config
        self.logger.info(f"Set active config to {client_id}:{dataset_id}")
    
    def get_active_config(self) -> Optional[BusinessConfiguration]:
        """Get the currently active configuration."""
        # If no active config, try to load from environment
        if not self.active_config:
            client_id = os.getenv("CLIENT_ID", "arizona_beverages")
            dataset_id = os.getenv("BIGQUERY_DATASET", "arizon-poc")
            self.set_active_config(client_id, dataset_id)
        
        return self.active_config
    
    def register_mapping_source(self, source_type: str, source_config: Dict[str, Any]):
        """Register a new mapping source."""
        # TODO: Implement support for different source types (API, DB, etc.)
        pass
    
    def update_mappings(self, mapping_type: str, mappings: Any):
        """Update specific mappings in the active configuration."""
        if not self.active_config:
            raise ValueError("No active configuration set")
        
        if mapping_type == "gl_mappings":
            self.active_config.gl_mappings = mappings
        elif mapping_type == "material_hierarchy":
            self.active_config.material_hierarchy = mappings
        elif mapping_type == "business_rules":
            self.active_config.business_rules = mappings
        
        self.save_config(self.active_config)
    
    def get_active_mappings(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get mappings relevant to the current query context."""
        if not self.active_config:
            return {}
        
        mappings = {
            "gl_mappings": self.active_config.gl_mappings,
            "material_hierarchy": self.active_config.material_hierarchy,
            "business_rules": self.active_config.get_active_rules()
        }
        
        return mappings
    
    def validate_configuration(self, config: BusinessConfiguration) -> List[str]:
        """Validate a business configuration."""
        return config.validate()
    
    def list_configurations(self) -> List[Dict[str, str]]:
        """List all available configurations."""
        configs = []
        for config_file in self.config_dir.glob("*.json"):
            parts = config_file.stem.split("_", 1)
            if len(parts) == 2:
                configs.append({
                    "client_id": parts[0],
                    "dataset_id": parts[1],
                    "file": str(config_file)
                })
        return configs