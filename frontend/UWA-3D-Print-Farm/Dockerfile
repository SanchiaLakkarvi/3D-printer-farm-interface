# Local Compose image for the Vinext/Vite UI (dev server).
# Browser talks to the API at NEXT_PUBLIC_API_BASE_URL (host-reachable origin).
FROM node:22.14-bookworm-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV HOST=0.0.0.0
ENV PORT=5173
# Default for Compose; override in docker-compose.yml. Browser must reach the API on the host.
ENV NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
