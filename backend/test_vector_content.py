"""Test what's actually in the vector embeddings."""

from src.db.weaviate_client import WeaviateClient
import weaviate.classes as wvc
import json

print("=" * 80)
print("VECTOR CONTENT INSPECTION")
print("=" * 80)
print()

# Connect to Weaviate
client = WeaviateClient()
collection = client.client.collections.get("TableSchemas")

# Get a few sample vectors to inspect
tables_to_check = ["transaction_data", "GL_Accounts", "customer_master_analysis"]

for table_name in tables_to_check:
    print("=" * 80)
    print(f"Table: {table_name}")
    print("=" * 80)

    try:
        response = collection.query.fetch_objects(
            filters=wvc.query.Filter.by_property("table_name").equal(table_name),
            limit=1
        )

        if response.objects and len(response.objects) > 0:
            obj = response.objects[0]
            props = obj.properties

            print(f"\n✅ Found vector for {table_name}")
            print(f"\nRow Count: {props.get('row_count', 'N/A')}")
            print(f"Column Count: {props.get('column_count', 'N/A')}")
            print(f"Has Relationships: {props.get('has_relationships', False)}")

            # Check business domains
            domains_json = props.get('business_domains', '[]')
            domains = json.loads(domains_json) if domains_json else []
            print(f"Business Domains: {domains if domains else 'None'}")

            # Check combined text (the enriched description)
            combined_text = props.get('combined_text', '')
            print(f"\nEnriched Description Length: {len(combined_text)} chars")
            print(f"\nFirst 500 chars of enriched text:")
            print("-" * 80)
            print(combined_text[:500])
            print("-" * 80)

            # Check if relationships are mentioned
            if "Relationships:" in combined_text:
                print("\n✅ Relationships ARE included in vector!")
                # Extract relationship section
                rel_start = combined_text.find("Relationships:")
                rel_section = combined_text[rel_start:rel_start+500]
                print(rel_section)
            else:
                print("\n⚠️  Relationships NOT found in vector text!")

            # Check if use cases are mentioned
            if "Common Use Cases:" in combined_text:
                print("\n✅ Use cases ARE included!")
            else:
                print("\n⚠️  Use cases NOT found!")

        else:
            print(f"\n❌ No vector found for {table_name}")

    except Exception as e:
        print(f"\n❌ Error checking {table_name}: {e}")
        import traceback
        traceback.print_exc()

    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print("If Relationships appear in the enriched text, RDF enhancement is working!")
print("If not, the RDF graph may not have the data, or query_relationships() is failing.")
print()

client.close()
