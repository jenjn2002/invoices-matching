from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS to allow requests from your frontend

@app.route("/process-pdf", methods=["POST"])
def process_pdf():
    # Check if a file is uploaded
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    
    # Validate that the file is a PDF
    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    # Simulate processing the PDF by returning a hardcoded JSON response
    # In a real backend, this would parse the PDF and extract the data
    mock_response = {
        "mst": "0100366745",
        "vendor": "CÔNG TY TNHH DƯỢC PHẨM ĐA PHÚC",
        "item_des": [
            {"id": "1", "product_name": "Enterogermina 2 billion/5ml (20 ống/H)"},
            {"id": "2", "product_name": "Refresh-tears mắt 15ml HQ."}
        ]
    }

    return jsonify(mock_response), 200

if __name__ == "__main__":
    app.run(debug=True, port=5001)