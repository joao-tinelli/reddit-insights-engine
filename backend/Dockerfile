FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend/ backend/
COPY execution/ execution/
COPY requirements.txt .

# Ensure log directory exists
RUN mkdir -p tmp

EXPOSE 8002

# Start FastAPI server
CMD ["python", "-u", "backend/main.py"]
