FROM python:3.12-slim

ENV AETHER_PORT=5467 \
    AETHER_HOST=0.0.0.0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Backend
COPY backend ./backend
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Frontend (Node build)
COPY frontend ./frontend
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && \
    cd frontend && npm install && npm run build && \
    apt-get remove -y nodejs npm && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# DB init
RUN cd backend && python - <<'PY'
import sys
sys.path.insert(0, "app")
from database import init_schema
from config import ensure_dirs
ensure_dirs()
init_schema()
PY

EXPOSE 5467
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5467"]
