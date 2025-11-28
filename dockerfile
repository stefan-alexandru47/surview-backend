# Use Python 3.9 as the base image
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies needed for OpenCV and other libraries
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (this helps with Docker caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire application code to the container
COPY . .

# Create directories that your app needs
RUN mkdir -p uploads processed

# Expose port 8080 (Google Cloud Run uses this port)
EXPOSE 8080

# Command to start your FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]