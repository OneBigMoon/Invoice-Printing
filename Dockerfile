FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV OCR_HOST=0.0.0.0
ENV OCR_PORT=8765

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libgomp1 \
      curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY index.html print.html i18n.js ocr_server.py favicon.svg favicon.ico apple-touch-icon.png icon-192.png icon-512.png site.webmanifest ./

EXPOSE 4173 8765

CMD ["sh", "-c", "python -m http.server 4173 --bind 0.0.0.0 & python ocr_server.py"]
