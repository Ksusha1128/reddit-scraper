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

# Render sets PORT env var (default 10000)
ENV PORT=10000

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/_stcore/health || exit 1

CMD streamlit run src/dashboard/app.py \
    --server.port=${PORT} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
