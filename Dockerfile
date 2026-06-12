FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD ["sh", "-c", "python3 -c 'import os, urllib.request; urllib.request.urlopen(\"http://127.0.0.1:%s/health\" % os.getenv(\"PORT\", \"8000\"), timeout=5)'" ]

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]

