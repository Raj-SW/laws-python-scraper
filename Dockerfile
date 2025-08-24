FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Default to headless in containers
    HEADLESS=true \
    # Make Playwright install browsers into image
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# System deps and init
RUN apt-get update && apt-get install -y --no-install-recommends \
    dumb-init curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

# Create non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Copy source
COPY . .

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python", "-m", "scraper.cli"]

