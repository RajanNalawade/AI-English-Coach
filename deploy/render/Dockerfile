# Small image for a free Render web service (512 MB RAM): the backend serves the PWA itself,
# and the model and speech-to-text run on a hosted API (Groq). See docs/RENDER.md.
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY backend/app ./app
COPY --from=web /web/dist /srv

# Free instances have no persistent disk, so the mistake log lives in /tmp and resets on restarts.
ENV COACH_STATIC_DIR=/srv \
    COACH_DB=/tmp/coach.db
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
