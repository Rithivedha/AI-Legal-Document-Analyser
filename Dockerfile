FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create user for Hugging Face
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:${PATH}"

WORKDIR /app

# Copy requirements and install python packages
COPY --chown=user:user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN pip install --no-cache-dir groq python-multipart

# Create backend and frontend directories
RUN mkdir -p /app/backend/uploads /app/backend/chroma_db /app/frontend

# Copy python files to /app/backend
COPY --chown=user:user *.py /app/backend/

# Copy frontend web files to /app/frontend
COPY --chown=user:user index.html app.js style.css /app/frontend/

WORKDIR /app/backend

# Expose port 7860
EXPOSE 7860

# Launch uvicorn server on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]