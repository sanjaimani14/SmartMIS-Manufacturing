# Production Container for SmartMIS Manufacturing Intelligence
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/smartmis:/app \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies for report generation and network healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY smartmis/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pytest httpx uvicorn

# Copy application source code and template files
COPY . .

# Expose Streamlit application port
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Launch Streamlit application
CMD ["streamlit", "run", "smartmis/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
