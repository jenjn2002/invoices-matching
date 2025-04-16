import torch
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from flask_cors import CORS
import typesense
import os
from dotenv import load_dotenv
import json
import numpy as np
from scipy.spatial.distance import cosine
import re
import unicodedata

load_dotenv()

app = Flask(__name__)
CORS(app)

# Load model
model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder", device="cpu")
model.eval()

# Connect to Typesense
client = typesense.Client({
    "nodes": [{
        "host": os.getenv("TYPESENSE_HOST"),
        "port": int(os.getenv("TYPESENSE_PORT")),
        "protocol": os.getenv("TYPESENSE_PROTOCOL")
    }],
    "api_key": os.getenv("TYPESENSE_API_KEY"),
    "connection_timeout_seconds": 2
})

# File to store mappings
MAPPING_FILE = "mappings.json"

# Enhanced query normalization function
def normalize_query(query, for_embedding=True):
    if not query:
        return ""
    query = unicodedata.normalize('NFKD', query).encode('ASCII', 'ignore').decode('ASCII')
    query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)
    query = re.sub(r'\s+', ' ', query).lower().strip()
    if for_embedding:
        tokens = query.split()
        tokens = [token for token in tokens if len(token) > 2 or token in ['20', 'h', '2']]
        query = ' '.join(tokens)
    return query

@app.route("/search", methods=["POST"])
def search():
    # Log the raw request headers and body for debugging
    print("Request headers:", request.headers)
    print("Request body:", request.get_data(as_text=True))

    # Handle both file uploads and JSON payloads
    if "file" in request.files:
        file = request.files["file"]
        if not file.filename.endswith(".json"):
            return jsonify({"error": "File must be a JSON file"}), 400
        try:
            data = json.load(file)
        except Exception as e:
            return jsonify({"error": f"Invalid JSON file: {str(e)}"}), 400
    else:
        # Handle JSON payload directly
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

    # Validate the JSON format
    if "item_des" not in data or not isinstance(data["item_des"], list):
        return jsonify({"error": "JSON must contain an 'item_des' list of products"}), 400

    try:
        results = []
        for item in data["item_des"]:
            if not isinstance(item, dict) or "id" not in item or "product_name" not in item:
                continue

            query = item["product_name"]
            item_id = item["id"]

            if not query.strip():
                print(f"⚠️ Skipping item with empty query (id: {item_id})")
                continue

            query_normalized_for_embedding = normalize_query(query, for_embedding=True)
            query_normalized_for_text = normalize_query(query, for_embedding=False)
            
            print(f"📥 Original query: {query}")
            print(f"🔧 Normalized for embedding: {query_normalized_for_embedding}")
            print(f"🔧 Normalized for text search: {query_normalized_for_text}")

            try:
                embedding = model.encode(
                    query_normalized_for_embedding or query_normalized_for_text, 
                    convert_to_numpy=True, 
                    normalize_embeddings=True
                ).tolist()
                if len(embedding) != 768 or np.allclose(embedding, 0):
                    raise ValueError("Invalid embedding generated")
                print("🔢 Query embedding (first 5):", embedding[:5])
            except Exception as e:
                print(f"❌ Failed to generate embedding for query '{query}': {e}")
                embedding = None

            main_product_name = query_normalized_for_text.split()[0]

            if embedding:
                multi_search_request = {
                    "searches": [{
                        "collection": "products",
                        "q": query_normalized_for_text,
                        "query_by": "name",
                        "query_by_weights": "3",
                        "vector_query": f"name_embedding:({embedding}, k:400, ef_search:1000)",
                        "filter_by": f"name:*{main_product_name}*",
                        "per_page": 10,
                        "prefix": True,
                        "infix": "always",
                        "sort_by": "_text_match:desc,_vector_distance:asc",
                        "drop_tokens_threshold": 1,
                        "typo_tokens_threshold": 2,
                        "num_typos": 2,
                        "min_len_1typo": 3,
                        "min_len_2typos": 5
                    }]
                }

                try:
                    search_results = client.multi_search.perform(multi_search_request, {})
                    hits = search_results.get("results", [{}])[0].get("hits", [])
                    print(f"✅ Hybrid search successful for query '{query}' (normalized: '{query_normalized_for_text}'): {len(hits)} hits")
                    for hit in hits[:3]:
                        doc = hit["document"]
                        text_score = hit.get("text_match", 0)
                        vector_distance = hit.get("vector_distance", float('inf'))
                        print(f"Match: {doc['name']} (Text Score: {text_score}, Vector Distance: {vector_distance})")
                except Exception as e:
                    print(f"❌ Hybrid search failed for query '{query}': {e}")
                    hits = []
            else:
                hits = []

            if not hits:
                search_request = {
                    "q": query_normalized_for_text,
                    "query_by": "name",
                    "query_by_weights": "3",
                    "filter_by": f"name:*{main_product_name}*",
                    "per_page": 10,
                    "prefix": True,
                    "infix": "always",
                    "sort_by": "_text_match:desc",
                    "drop_tokens_threshold": 1,
                    "typo_tokens_threshold": 2,
                    "num_typos": 2,
                    "min_len_1typo": 3,
                    "min_len_2typos": 5
                }

                try:
                    search_results = client.collections["products"].documents.search(search_request)
                    hits = search_results.get("hits", [])
                    print(f"✅ Text search successful for query '{query}' (normalized: '{query_normalized_for_text}'): {len(hits)} hits")
                    for hit in hits[:3]:
                        doc = hit["document"]
                        text_score = hit.get("text_match", 0)
                        print(f"Match: {doc['name']} (Text Score: {text_score})")
                except Exception as e:
                    print(f"❌ Text search failed for query '{query}': {e}")
                    hits = []

            for hit in hits:
                doc = hit["document"]
                hit["document"] = {
                    "id": doc["id"],
                    "name": doc["name"],
                    "barcode": doc["barcode"],
                    "unit": doc["unit"]
                }

            results.append({
                "id": item_id,
                "query": query,
                "matches": hits
            })

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

@app.route("/save-mapping", methods=["POST"])
def save_mapping():
    mappings = request.get_json()
    if not mappings:
        return jsonify({"error": "No mappings provided"}), 400

    try:
        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(mappings, f, ensure_ascii=False, indent=4)
        return jsonify({"message": "Mappings saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to save mappings: {str(e)}"}), 500

@app.route("/debug-embedding/<doc_id>", methods=["GET"])
def debug_embedding(doc_id):
    try:
        doc = client.collections["products"].documents[doc_id].retrieve()
        return jsonify({
            "id": doc["id"],
            "name": doc["name"],
            "name_embedding": doc["name_embedding"]
        })
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve document: {str(e)}"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)