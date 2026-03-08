FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Python deps — install first for Docker cache
COPY requirements-render.txt .
RUN pip install --no-cache-dir -r requirements-render.txt

# Copy source code & data
COPY src/ ./src/
COPY reviews/ ./reviews/
COPY .streamlit/ ./.streamlit/

# Hugging Face Spaces expects the app to listen on port 7860
ENV PORT=7860

EXPOSE 7860

CMD streamlit run src/dashboard/app.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
