# Use the official Python image as the base
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the mock backend files
COPY . .

# Expose port 5001 for the Flask app
EXPOSE 5001

# Command to run the Flask app
CMD ["python", "mock_backend.py"]