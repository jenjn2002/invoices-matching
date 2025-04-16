from typesense import Client
import os
from dotenv import load_dotenv

load_dotenv()

client = Client({
    "nodes": [{
        "host": os.getenv("TYPESENSE_HOST"),
        "port": os.getenv("TYPESENSE_PORT"),
        "protocol": os.getenv("TYPESENSE_PROTOCOL")
    }],
    "api_key": os.getenv("TYPESENSE_API_KEY"),
    "connection_timeout_seconds": 2
})

# In thông tin schema
schema = client.collections["products"].retrieve()
print("📦 Schema của collection 'products':")
print(schema)
