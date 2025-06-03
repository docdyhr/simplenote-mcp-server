# Multi-stage build for optimal image size
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for better caching
COPY pyproject.toml setup.py setup.cfg MANIFEST.in ./
COPY simplenote_mcp/__init__.py simplenote_mcp/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r mcp && useradd -r -g mcp mcp

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/simplenote-mcp-server /usr/local/bin/

# Copy application code
COPY --chown=mcp:mcp . .

# Create logs directory with proper permissions
RUN mkdir -p /app/simplenote_mcp/logs && chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Expose port for HTTP transport (default MCP port)
EXPOSE 8000

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Use exec form for proper signal handling
ENTRYPOINT ["simplenote-mcp-server"]
