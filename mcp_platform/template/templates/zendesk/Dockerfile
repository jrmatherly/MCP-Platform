FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
  python -c "import sys, urllib.request; \
  sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:7072/health').getcode() == 200 else sys.exit(1)"

# Expose port
EXPOSE 7072

# Run the server
CMD ["python", "server.py"]
