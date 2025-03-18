FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt update && apt install -y libffi-dev && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ /app/app/
COPY data/ /app/data/
COPY static/ /app/static/
COPY templates/ /app/templates/
COPY webui.py main.py ./

# Create empty storage directory
RUN mkdir -p /app/storage

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "main.py"]
