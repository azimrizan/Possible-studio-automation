FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings httpx cryptography

COPY packages/mcp-common /app/packages/mcp-common
RUN pip install -e /app/packages/mcp-common

COPY mcp-servers/mcp-media /app/mcp-servers/mcp-media

ENV PYTHONPATH=/app/packages/mcp-common:/app/mcp-servers/mcp-media
EXPOSE 8104

CMD ["python", "/app/mcp-servers/mcp-media/media_server.py"]
