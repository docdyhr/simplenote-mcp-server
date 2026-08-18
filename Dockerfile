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
# CACHE_DATE busts the BuildKit layer cache weekly (passed as %Y-W%V from CI)
# so apt-get upgrade always hits a live mirror at least once a week instead of
# silently reusing a stale cached layer indefinitely (cache-to: mode=max has
# no built-in expiry).
ARG CACHE_DATE
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml ./
COPY setup.py ./
COPY VERSION ./
COPY requirements-runtime-lock.txt ./

# Install build dependencies first (setuptools>=78.1.1 for jaraco.context CVE fix).
# The standalone `build` package isn't needed: `pip install .` on a PEP
# 517 project builds via its own isolated build environment.
RUN pip install --no-cache-dir --upgrade pip "setuptools>=78.1.1" "wheel>=0.46.2"

# Copy source code
COPY simplenote_mcp/ simplenote_mcp/

# Install pinned runtime dependencies, then the package itself without
# re-resolving deps. Deliberately NOT `.[all]` — that extra pulls in
# ruff/mypy/bandit/pytest/pre-commit/twine/build and more, none of which
# belong in a production image (see requirements-runtime-lock.txt).
RUN pip install --no-cache-dir -r requirements-runtime-lock.txt \
    && pip install --no-cache-dir --no-deps .

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
# CACHE_DATE busts the BuildKit layer cache weekly, see builder stage above.
ARG CACHE_DATE
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder. Only the package's own console-script
# entry point is copied from /usr/local/bin — not the full directory, which
# would also pull in build-time-only CLI tools (pip, wheel, typer, uvicorn,
# mcp, keyring, jsonschema, pygmentize, idle, pydoc, etc.) that the runtime
# image has no use for and that needlessly grow its attack surface. The
# entrypoint's `python -m simplenote_mcp` fallback needs no console script at
# all, and the script's shebang (/usr/local/bin/python3.13) resolves against
# this stage's own base-image Python.
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages
COPY --from=builder /usr/local/bin/simplenote-mcp-server /usr/local/bin/simplenote-mcp-server

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

# Real health check against the monitoring server (requires
# ENABLE_HTTP_ENDPOINT=true, HTTP_PORT=8080 — see README) — an import-only
# check proves the package is installed, not that the process is serving
# anything. No curl in this image, so a Python one-liner.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=5).status == 200 else 1)"

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
