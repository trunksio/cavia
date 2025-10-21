# Dockerfile for CAVIA DB Writer Worker (Non-Agentic Unit)

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install shared package
COPY shared/python /shared
RUN pip install --no-cache-dir -e /shared

# Copy db-writer worker code
COPY workers/db_writer/ /app/

# Set Python path
ENV PYTHONPATH="/shared:/app:${PYTHONPATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run worker
CMD ["python", "main.py"]
