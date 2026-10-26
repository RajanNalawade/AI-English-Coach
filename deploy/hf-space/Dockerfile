# One container for a free Hugging Face Docker Space (CPU basic: 2 vCPU, 16 GB RAM):
# Ollama + the coach backend + the PWA, behind Caddy with a password.
# Build context is the repository root (see .github/workflows/hf-space.yml).
ARG OLLAMA_VERSION=0.40.11

FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM ollama/ollama:${OLLAMA_VERSION} AS ollama
# Keep only the CPU libraries; the GPU ones add about 4 GB.
RUN rm -rf /usr/lib/ollama/cuda_* /usr/lib/ollama/mlx_* /usr/lib/ollama/vulkan /usr/lib/ollama/include

FROM caddy:2 AS caddy

FROM python:3.12-slim-trixie
ARG COACH_MODEL=qwen3:4b
ARG COACH_STT_MODEL=base

COPY --from=ollama /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama /usr/lib/ollama /usr/lib/ollama
COPY --from=caddy /usr/bin/caddy /usr/bin/caddy

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=web /web/dist /srv
COPY deploy/hf-space/Caddyfile /etc/caddy/Caddyfile
COPY deploy/hf-space/start.sh /start.sh

# Bake both models into the image so a restart doesn't download them again.
ENV OLLAMA_MODELS=/opt/ollama/models \
    HF_HOME=/opt/hf \
    COACH_MODEL=${COACH_MODEL} \
    COACH_STT_MODEL=${COACH_STT_MODEL}
RUN (ollama serve >/dev/null 2>&1 &) \
    && for i in $(seq 1 30); do ollama list >/dev/null 2>&1 && break; sleep 1; done \
    && ollama pull "$COACH_MODEL" \
    && python -c "from faster_whisper import WhisperModel; WhisperModel('$COACH_STT_MODEL', device='cpu', compute_type='int8')" \
    && chmod -R a+rwX /opt/ollama /opt/hf

# Spaces run the container as user 1000 with a read-only image; keep state in /tmp.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    XDG_CONFIG_HOME=/tmp/caddy-config \
    XDG_DATA_HOME=/tmp/caddy-data \
    COACH_DB=/tmp/coach.db \
    COACH_KEEP_ALIVE=-1 \
    OLLAMA_NOPRUNE=true \
    PORT=7860
EXPOSE 7860
CMD ["bash", "/start.sh"]
