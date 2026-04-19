# Multi-stage build for optimal image size and security
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim AS builder

# Build arguments for metadata
ARG BUILDTIME
ARG VERSION
ARG REVISION
ARG PYTHON_VERSION

WORKDIR /app

# Install build dependencies (upgrade first to pick up latest security patches)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml ./
COPY setup.py ./
COPY VERSION ./

# Install build dependencies first (setuptools>=78.1.1 for jaraco.context CVE fix)
RUN pip install --no-cache-dir --upgrade pip "setuptools>=78.1.1" "wheel>=0.46.2" build

# Copy source code
COPY simplenote_mcp/ simplenote_mcp/

# Build and install the package properly
RUN pip install --no-cache-dir .[all]

# Production stage
ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

# Build arguments for metadata
ARG BUILDTIME
ARG VERSION
ARG REVISION
ARG PYTHON_VERSION

# Create non-root user for security
RUN groupadd -g 1000 mcp && useradd -u 1000 -g mcp -m -d /home/mcp mcp

WORKDIR /app

# Apply security updates and install minimal runtime dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code with proper ownership
COPY --chown=mcp:mcp simplenote_mcp/ ./simplenote_mcp/
COPY --chown=mcp:mcp pyproject.toml setup.py VERSION ./

# Create logs directory with proper permissions
RUN mkdir -p /app/logs /home/mcp/.local/share/simplenote-mcp \
    && chown -R mcp:mcp /app /home/mcp/.local

# Switch to non-root user
USER mcp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV HOME=/home/mcp

# Expose port for HTTP transport (default MCP port)
EXPOSE 8000

# Add health check that actually tests the module import
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import simplenote_mcp.server; print('Health check passed')" || exit 1

# Add metadata labels
LABEL org.opencontainers.image.created="${BUILDTIME}"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${REVISION}"
LABEL org.opencontainers.image.title="Simplenote MCP Server"
LABEL org.opencontainers.image.description="A Model Context Protocol server for Simplenote integration"
LABEL org.opencontainers.image.vendor="Thomas Juul Dyhr"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.url="https://github.com/docdyhr/simplenote-mcp-server"
LABEL org.opencontainers.image.source="https://github.com/docdyhr/simplenote-mcp-server"

# Copy entrypoint script with proper ownership
COPY --chown=mcp:mcp docker-entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Use exec form for proper signal handling
ENTRYPOINT ["/app/entrypoint.sh"]
