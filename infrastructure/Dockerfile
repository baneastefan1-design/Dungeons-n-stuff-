FROM python:3.12-slim

WORKDIR /app
COPY infrastructure/requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt
COPY backend ./backend
COPY frontend ./frontend

EXPOSE 8080
CMD ["uvicorn", "backend.web_server:app", "--host", "0.0.0.0", "--port", "8080"]
