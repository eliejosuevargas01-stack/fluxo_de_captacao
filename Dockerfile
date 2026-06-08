FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libnss3 \
    libxss1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python3 -m playwright install --with-deps chromium
RUN ls -la /root/.cache/ms-playwright/ || echo "Playwright cache not found"
RUN python3 -c "from playwright.sync_api import sync_playwright; print('Playwright import OK')"

COPY . .

ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)"

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
