FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
# Copying here makes the image self-contained if used alone.
COPY . .

# Environment variables for default connection
ENV DB_DSN=postgresql://postgres:postgres@db:5432/postgres
ENV OLLAMA_HOST=http://ollama:11434

# Default command (overridden in compose to keep container alive)
CMD ["bash"]
