FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Python package
COPY pyproject.toml README.md ./
COPY flowforge/ ./flowforge/
COPY examples/ ./examples/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create output and volume directories
RUN mkdir -p /app/data /app/output /app/workflows

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["flowforge", "serve", "--host", "0.0.0.0", "--port", "8000", "--workflows-dir", "/app/examples", "--db", "/app/data/flowforge.db"]
