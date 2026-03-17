FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
COPY examples/ examples/

RUN pip install --no-cache-dir -e ".[web]"

EXPOSE 8000

CMD ["radio-drama-web", "--host", "0.0.0.0", "--port", "8000"]
