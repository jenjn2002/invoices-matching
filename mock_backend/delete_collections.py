import os
from dotenv import load_dotenv
import typesense

# Tải các biến môi trường từ .env
load_dotenv()

# Lấy các giá trị từ môi trường
typesense_host = os.getenv("TYPESENSE_HOST")
typesense_port = os.getenv("TYPESENSE_PORT")
typesense_protocol = os.getenv("TYPESENSE_PROTOCOL")
typesense_api_key = os.getenv("TYPESENSE_API_KEY")

# Khởi tạo client Typesense
client = typesense.Client({
    "nodes": [{
        "host": typesense_host,
        "port": typesense_port,
        "protocol": typesense_protocol
    }],
    "api_key": typesense_api_key,
    "connection_timeout_seconds": 2
})

# Hàm xóa collection
def delete_collection(collection_name):
    try:
        client.collections[collection_name].delete()
        print(f"✅ Collection '{collection_name}' đã được xóa.")
    except Exception as e:
        print(f"❌ Lỗi khi xóa collection: {e}")

# Nếu muốn chạy riêng lẻ:
if __name__ == "__main__":
    delete_collection("products")
