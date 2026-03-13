FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000

EXPOSE 8000

CMD ["python", "app.py"]
