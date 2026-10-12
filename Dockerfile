FROM python:3.12-slim

# Python runtime configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (OpenCV headless & video support, netcat, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-traditional \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Ensure media and static storage directories exist and entrypoint is executable
RUN mkdir -p /app/media /app/staticfiles && \
    chmod +x /app/scripts/docker-entrypoint.sh && \
    useradd -m -u 10001 -s /bin/bash athena && \
    chown -R athena:athena /app

USER athena

EXPOSE 8000

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "180"]
