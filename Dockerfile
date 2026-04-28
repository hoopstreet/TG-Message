# Use a slim Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Telethon/SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Set the entry point to your commander bot
CMD ["python", "send.py"]
