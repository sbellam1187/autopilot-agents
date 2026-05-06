FROM docker.aa.com/prod/aa.com/python:3.12-dev@sha256:227cad97533671c1d33f4ee51eea8eb1833f236875274ebbf29b1027b8e708a2 AS builder

ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

RUN python -m venv /app/venv
COPY pyproject.toml poetry.lock ./

# Upgrade pip and install wheel for better dependency resolution
RUN . /app/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip wheel poetry && \
    poetry install --no-root

FROM docker.aa.com/prod/aa.com/python:3.12@sha256:1e9ab88b7d8dc7746463aec6e2c15ad6bbb49b89b85a1421a7badbabd2a41ac6

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/venv/bin:$PATH"

COPY . .
COPY --from=builder /app/venv /venv

EXPOSE 8000

ENTRYPOINT [ "python", "/app/app/server.py" ]