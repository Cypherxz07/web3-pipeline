FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 5000
CMD ["sh", "-c", "python -m whale_tracker.whale_api & python -m whale_tracker.main"]