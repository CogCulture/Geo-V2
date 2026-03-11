FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . .

# Set environment variables
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000
ENV RELOAD=false

EXPOSE 8000

# Run the application
CMD ["python", "app.py"]