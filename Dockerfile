# --- STAGE 1: Builder Stage ---
# Use a lightweight official Python image for building dependencies
FROM python:3.11-slim as builder

# Set the working directory inside the container
WORKDIR /app

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies needed for some Python packages (optional, but good practice)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install uvicorn

COPY api /app/api
COPY core /app/core
COPY db /app/db
COPY models /app/models
COPY services /app/services
COPY app.py /app/app.py
COPY .env /app/.env

EXPOSE 8000
# Command to run the application using Uvicorn in production mode.
# We bind to 0.0.0.0 to make it accessible outside the container and use 4 workers
# for parallel processing (recommended: 2x number of CPU cores).
# The syntax is 'module:variable' (app.py and app = FastAPI())
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]