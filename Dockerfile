FROM python:3.12-slim

ARG DENO_VERSION=2.9.7
ARG BGUTIL_VERSION=2.0.0
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl unzip ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# JavaScript runtime used by yt-dlp's current YouTube extractor.
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

# Local Proof-of-Origin token provider used by yt-dlp for YouTube requests.
# The provider runs only inside this container on 127.0.0.1:4416.
RUN git clone --depth 1 --single-branch --branch "${BGUTIL_VERSION}" \
      https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
      /opt/bgutil-ytdlp-pot-provider \
    && cd /opt/bgutil-ytdlp-pot-provider/server \
    && deno install --allow-scripts=npm:canvas --frozen

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY start.sh .
RUN chmod +x /app/start.sh && mkdir -p /app/downloads

EXPOSE 10000
CMD ["/app/start.sh"]
