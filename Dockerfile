FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/ ./backend/
RUN pip install --no-cache-dir -r backend/requirements.lock && pip install --no-deps ./backend
COPY --from=frontend /build/frontend/dist ./frontend/dist
# Editable install preserves the repository-relative static directory.
RUN pip install --no-deps -e ./backend && useradd --create-home sectorpulse && mkdir -p /app/data && chown sectorpulse:sectorpulse /app/data
USER sectorpulse
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
