FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project code and web frontend
COPY . .

# Ensure storage directories exist with write permissions
RUN mkdir -p uploads chroma_db && chmod -R 777 uploads chroma_db

# Default Render port is 10000; can be overridden by PORT env variable
ENV PORT=10000
EXPOSE 10000

# Start Uvicorn dynamically binding to the port provided by Render ($PORT)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]