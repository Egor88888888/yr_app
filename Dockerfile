# 🐳 PRODUCTION DOCKERFILE - NO AZURE AI VERSION 2.0
# Force complete rebuild to eliminate Azure dependencies

FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r app && useradd -r -g app app

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements_frozen.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements_frozen.txt

# Copy application code
COPY . .

# FORCE REMOVE any Azure AI files that might still exist
RUN rm -rf bot/services/ai_enhanced* 2>/dev/null || true
RUN rm -rf bot/**/__pycache__ 2>/dev/null || true
RUN find . -name "*.pyc" -delete 2>/dev/null || true

# Create necessary directories
RUN mkdir -p logs && chown -R app:app logs
RUN mkdir -p webapp && chown -R app:app webapp

# Change to app user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Start command - CLEAN VERSION WITHOUT AI_ENHANCED
CMD ["python", "start_clean.py"] 