from sentence_transformers import SentenceTransformer
import psycopg2
import typesense
import os
from dotenv import load_dotenv
import numpy as np
import re
import unicodedata

load_dotenv()

# Initialize model for embeddings
model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder", device="cpu")
model.eval()

# Connect to Typesense
client = typesense.Client({
    "nodes": [{
        "host": os.getenv("TYPESENSE_HOST"),
        "port": os.getenv("TYPESENSE_PORT"),
        "protocol": os.getenv("TYPESENSE_PROTOCOL")
    }],
    "api_key": os.getenv("TYPESENSE_API_KEY"),
    "connection_timeout_seconds": 2
})

# Enhanced query normalization function (same as in app.py)
def normalize_query(query, for_embedding=True):
    # Step 1: Normalize diacritics (e.g., "mắt" -> "mat")
    query = unicodedata.normalize('NFKD', query).encode('ASCII', 'ignore').decode('ASCII')
    
    # Step 2: Replace special characters with spaces
    query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)
    
    # Step 3: Replace multiple spaces with a single space and lowercase
    query = re.sub(r'\s+', ' ', query).lower().strip()
    
    # Step 4: For embedding, remove small tokens like "l", "hq", "15ml" to focus on core terms
    if for_embedding:
        tokens = query.split()
        tokens = [token for token in tokens if len(token) > 2 and token not in ['15ml', 'hq', 'mat', 'l']]
        query = ' '.join(tokens)
    
    return query

# Create collection with only the required fields
def create_collection():
    schema = {
        "name": "products",
        "fields": [
            {"name": "id", "type": "string"},  # Mã hàng
            {"name": "name", "type": "string", "token_separators": ["-", ".", "/", "(", ")", "l"], "symbols_to_index": [], "infix": True},  # Tên hàng
            {"name": "barcode", "type": "string", "optional": True},  # Mã vạch
            {"name": "unit", "type": "string", "optional": True},  # ĐVT (Unit of measurement)
            {"name": "name_embedding", "type": "float[]", "num_dim": 768}  # Embedding for name
        ],
        "hnsw_params": {"M": 32, "ef_construction": 400}  # Improved indexing
    }

    try:
        client.collections["products"].delete()
        print("🗑️ Deleted existing products collection")
    except Exception:
        print("ℹ️ No existing products collection to delete")

    client.collections.create(schema)
    print("📦 Created products collection with infix enabled")

# Fetch data from PostgreSQL with only the required fields
def fetch_data():
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_URL"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )
        cur = conn.cursor()
        # Fetch only the required columns: Mã hàng, Mã vạch, Tên hàng, ĐVT
        cur.execute('SELECT "Mã hàng", "Mã vạch", "Tên hàng", "ĐVT" FROM cr_product.cr_product')
        rows = cur.fetchall()
        conn.close()
        print(f"📥 Fetched {len(rows)} rows from PostgreSQL")
        return rows
    except Exception as e:
        print(f"❌ Failed to fetch data from PostgreSQL: {e}")
        return []

# Import data
def import_data():
    create_collection()
    rows = fetch_data()
    if not rows:
        print("⚠️ No data to import")
        return

    # Batch import
    batch_size = 100
    documents = []
    for row in rows:
        name = row[2] or ""  # Tên hàng
        name_normalized = normalize_query(name, for_embedding=True)
        embedding = model.encode(name_normalized, normalize_embeddings=True).tolist() if name else [0.0] * 768
        if name and (len(embedding) != 768 or np.allclose(embedding, 0)):
            print(f"❌ Invalid embedding for {name}")
            continue
        doc = {
            "id": str(row[0]) if row[0] else f"missing_id_{len(documents)}",  # Mã hàng
            "name": name,  # Tên hàng
            "barcode": str(row[1]) if row[1] else "",  # Mã vạch
            "unit": row[3] or "",  # ĐVT
            "name_embedding": embedding
        }
        documents.append(doc)

        if len(documents) >= batch_size:
            try:
                client.collections["products"].documents.import_(documents, {"action": "create"})
                print(f"✅ Imported batch of {len(documents)} documents")
                documents = []
            except Exception as e:
                print(f"❌ Failed to import batch: {e}")
                for doc in documents:
                    try:
                        client.collections["products"].documents.create(doc)
                        print(f"✅ Fallback: Imported {doc['name']}")
                    except Exception as e:
                        print(f"❌ Failed to import {doc['name']}: {e}")
                documents = []

    if documents:
        try:
            client.collections["products"].documents.import_(documents, {"action": "create"})
            print(f"✅ Imported final batch of {len(documents)} documents")
        except Exception as e:
            print(f"❌ Failed to import final batch: {e}")

    print(f"✅ Imported {len(rows)} documents to Typesense")

if __name__ == "__main__":
    import_data()