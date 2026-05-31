FROM python:3.11-slim

LABEL maintainer="HFIP Team"
LABEL description="Healthcare Funding Intelligence Platform"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose Streamlit port
EXPOSE 8501

# Default command: run the scheduler + dashboard
CMD ["python", "main.py"]
