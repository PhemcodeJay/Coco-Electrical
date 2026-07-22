# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /opt/render/project/src

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create instance directory for database
RUN mkdir -p /opt/render/project/src/instance

# Expose port
EXPOSE 8000

# Start the application
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]