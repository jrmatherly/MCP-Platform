# Trino MCP Server - Python FastMCP implementation
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Default environment variables
ENV TRINO_HOST="trino" \
    TRINO_PORT="8080" \
    TRINO_USER="admin" \
    TRINO_SCHEME="https" \
    TRINO_SSL="true" \
    TRINO_SSL_INSECURE="true" \
    TRINO_ALLOW_WRITE_QUERIES="false" \
    TRINO_QUERY_TIMEOUT="300" \
    TRINO_MAX_RESULTS="1000" \
    MCP_TRANSPORT="http" \
    MCP_HOST="0.0.0.0" \
    MCP_PORT="7090"

# Expose the port
EXPOSE 7090

# Run the server
CMD ["python", "-m", "server"]
