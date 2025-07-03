# Multi-stage build for optimal image size
FROM python:3.13-slim AS builder

# Build arguments for metadata
ARG BUILDTIME
ARG VERSION
ARG REVISION

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for better caching
COPY pyproject.toml setup.py setup.cfg MANIFEST.in VERSION ./
COPY simplenote_mcp/ simplenote_mcp/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -e .[all]

# Production stage
FROM python:3.13-slim

# Build arguments for metadata
ARG BUILDTIME
ARG VERSION
ARG REVISION

# Create non-root user for security
RUN groupadd -r mcp && useradd -r -g mcp mcp

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
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
    CMD python -c "import simplenote_mcp; print('Health check passed')" || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Add metadata labels
LABEL org.opencontainers.image.created="${BUILDTIME}"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${REVISION}"
LABEL org.opencontainers.image.title="Simplenote MCP Server"
LABEL org.opencontainers.image.description="A Model Context Protocol server for Simplenote integration"
LABEL org.opencontainers.image.vendor="Thomas Juul Dyhr"
LABEL org.opencontainers.image.licenses="MIT"

# Use exec form for proper signal handling
ENTRYPOINT ["simplenote-mcp-server"]
