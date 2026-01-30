FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ backend/

# Copy frontend code
COPY frontend/ frontend/

# Set working directory to backend
WORKDIR /app/backend

# Create static directories
RUN mkdir -p static/uploads/images static/uploads/audio

# Expose port (HF Spaces uses 7860 by default)
EXPOSE 7860

# Run the application
# Use 0.0.0.0 and port 7860 (Hugging Face default)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
