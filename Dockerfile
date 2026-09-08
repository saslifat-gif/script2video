FROM python:3.11-slim-bookworm AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake pkg-config \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PIP_NO_CACHE_DIR=1
RUN pip install --upgrade pip && pip install 'torch>=2.2,<3' --index-url https://download.pytorch.org/whl/cpu
WORKDIR /app
COPY pyproject.toml ./
RUN python -c "import tomllib; p=tomllib.load(open('pyproject.toml','rb'))['project']; print('\n'.join(p['dependencies'] + p['optional-dependencies']['kokoro']))" > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt \
    && python -m spacy download en_core_web_sm
COPY README.md LICENSE ./
COPY src ./src
RUN pip install --no-deps .

FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends espeak-ng ffmpeg libsndfile1 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 studio \
    && mkdir -p /data/input /data/output /home/studio/.cache \
    && chown -R studio:studio /data /home/studio
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 SCRIPT2VIDEO_CONTAINER=1 \
    HF_HOME=/home/studio/.cache/huggingface
WORKDIR /data
USER studio
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8765/api/bootstrap', timeout=4)"
CMD ["script2video", "companion"]
