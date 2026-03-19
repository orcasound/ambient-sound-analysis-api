FROM python:3.9-slim

COPY --from=node:20-bookworm-slim /usr/local/ /usr/local/

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces
