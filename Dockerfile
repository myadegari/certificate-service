# --- Runtime image with LibreOffice for headless PDF conversion ---
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

# LibreOffice (Impress for .pptx, Writer for .docx) + font tooling + curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice-impress \
        libreoffice-writer \
        fonts-liberation \
        fontconfig \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Persian fonts used by the certificate/report templates
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
    mkdir -p tmp temp_certificates temp_reports && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
