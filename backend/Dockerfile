FROM python:3.12-slim AS bgcode-builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY backend/app/validation/setup_bgcode.sh ./backend/app/validation/setup_bgcode.sh
COPY backend/app/validation/cmake ./backend/app/validation/cmake

# Build the pinned official Prusa converter once, then copy only the executable
# into the runtime image. Uploaded .bgcode files require this for full safety
# and executable-command validation.
RUN bash backend/app/validation/setup_bgcode.sh


FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY Docs/help /app/help
COPY --from=bgcode-builder /build/backend/app/validation/.tools/bin/bgcode /usr/local/bin/bgcode

RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
