#!/bin/sh
set -eu

# Start the POT provider locally. yt-dlp's bgutil plugin defaults to this address.
cd /opt/bgutil-ytdlp-pot-provider/server/node_modules
deno run --allow-env --allow-net --allow-ffi=. --allow-read=. ../src/main.ts --host 127.0.0.1 --port 4416 >/tmp/bgutil.log 2>&1 &
PROVIDER_PID=$!
trap 'kill "$PROVIDER_PID" 2>/dev/null || true' EXIT INT TERM

# Wait briefly for the provider to accept connections.
i=0
while [ "$i" -lt 30 ]; do
  if curl -fsS http://127.0.0.1:4416/ >/dev/null 2>&1; then
    break
  fi
  i=$((i+1))
  sleep 1
done

cd /app
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-10000}"
