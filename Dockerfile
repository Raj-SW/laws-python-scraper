FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HEADLESS=true

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure permissions for default Playwright user (pwuser)
RUN chown -R pwuser:pwuser /app
USER pwuser

CMD ["python", "-m", "scraper.cli"]

