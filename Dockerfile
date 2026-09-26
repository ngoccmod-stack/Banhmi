FROM python:3.12-slim

ARG DENO_VERSION=2.9.7
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp now needs a supported JavaScript runtime for YouTube extraction.
# Install the current Deno release for either amd64 or arm64.
RUN set -eux; \
    case "${TARGETARCH:-amd64}" in \
      amd64) DENO_ARCH="x86_64" ;; \
      arm64) DENO_ARCH="aarch64" ;; \
      *) echo "Unsupported TARGETARCH: ${TARGETARCH}"; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/denoland/deno/releases/download/v${DENO_VERSION}/deno-${DENO_ARCH}-unknown-linux-gnu.zip" -o /tmp/deno.zip; \
    unzip -q /tmp/deno.zip -d /usr/local/bin; \
    chmod +x /usr/local/bin/deno; \
    rm -f /tmp/deno.zip; \
    deno --version

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
RUN mkdir -p downloads

EXPOSE 10000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
