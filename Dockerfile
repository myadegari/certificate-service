# --- Runtime image with LibreOffice for headless PDF conversion ---
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    LANG=fa_IR.UTF-8 \
    LC_ALL=fa_IR.UTF-8

# LibreOffice (Impress for .pptx) + Persian locale + font tooling + curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice-impress \
        libreoffice-l10n-fa \
        locales \
        fonts-liberation \
        fontconfig \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Generate the Persian locale (append the entry, then generate; the
# `locale-gen <name>` argument form is unreliable on this base image).
RUN echo "fa_IR.UTF-8 UTF-8" >> /etc/locale.gen && locale-gen

# Persian fonts used by the certificate template
COPY docker/fonts/ /usr/local/share/fonts/certificate-system/
RUN fc-cache -f

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py worker.py ./
COPY api/ ./api/
COPY core/ ./core/
COPY models/ ./models/
COPY services/ ./services/
COPY assets/ ./assets/
COPY templates/ ./templates/

RUN useradd -m appuser && \
    mkdir -p tmp temp_certificates && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
