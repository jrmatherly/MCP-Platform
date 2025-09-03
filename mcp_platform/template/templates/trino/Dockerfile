# Stage 1: Extract binary from upstream Trino MCP image
FROM ghcr.io/tuannvm/mcp-trino:latest AS trino-mcp

# Stage 2: Final image with shell support
FROM alpine

# Copy binary from Trino MCP image to Alpine
COPY --from=trino-mcp /server/mcp-trino /server/mcp-trino

# Copy and set up the script
COPY script.sh /server/script.sh
RUN chmod +x /server/script.sh

ENTRYPOINT ["/server/script.sh"]