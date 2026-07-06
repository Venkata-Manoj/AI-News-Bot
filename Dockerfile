# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (ffmpeg for yt-dlp, ca-certificates for HTTPS)
RUN apt-get update && apt-get install --no-install-recommends -y \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (layer caching)
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py main.py ./
COPY modules/ ./modules/

# Create data & log directories (persist via volumes)
RUN mkdir -p /app/data /app/logs

# Health check — verifies the bot can import and init
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import config, modules.db, modules.dedup, modules.llm, modules.sender; print('health ok')" || exit 1

# Default: run a single pipeline pass (test mode)
# Override CMD or use --schedule for production
ENTRYPOINT ["python", "main.py"]
CMD ["--schedule"]
