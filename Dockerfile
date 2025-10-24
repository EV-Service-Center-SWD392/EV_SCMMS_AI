# EV SCMMS AI - Multi-Service Dockerfile
# =======================================
# This Dockerfile builds a container for the EV SCMMS AI Chatbot service
# with integrated forecasting capabilities and MCP function calling.

# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    FLASK_ENV=production \
    FLASK_APP=ai_chatbot/chatbot_api.py

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app \
    && chown -R app:app /app

# Set working directory
WORKDIR /app

# Switch to non-root user
USER app

# Copy requirements first for better caching
COPY --chown=app:app ai_chatbot/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=app:app ai_chatbot/ ./ai_chatbot/
COPY --chown=app:app shared/ ./shared/

# Create logs directory
RUN mkdir -p /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8469/health || exit 1

# Expose ports
EXPOSE 8469

# Default command - run the chatbot service
CMD ["python", "-m", "ai_chatbot.chatbot_api"]

# Alternative commands (uncomment to use):
# CMD ["python", "-c", "from ai_chatbot.forecast_engine import run_forecast_sync; run_forecast_sync()"]
# CMD ["python", "test_integration.py"]