FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY packages/mcp-common /app/packages/mcp-common
RUN pip install --no-cache-dir /app/packages/mcp-common uvicorn

COPY mcp-servers/mcp-hello /app/mcp-servers/mcp-hello

ENV PYTHONPATH="/app:/app/packages/mcp-common:/app/mcp-servers/mcp-hello"
EXPOSE 8101

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8101"]
