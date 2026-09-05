FROM python:3.12-slim

WORKDIR /app
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt
COPY game.py pathfinding.py web_server.py ./
COPY assets ./assets
COPY favicon.png ./web/favicon.png
COPY web ./web

EXPOSE 8080
CMD ["uvicorn", "web_server:app", "--host", "0.0.0.0", "--port", "8080"]
