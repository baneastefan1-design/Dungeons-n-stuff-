# Build the Python/Pygame WebAssembly package, then serve it as static files.
FROM python:3.12-slim AS build

WORKDIR /game
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt
COPY . .
RUN python -m pygbag --build --title "Dungeon Escape" .

FROM nginx:1.27-alpine
COPY --from=build /game/build/web /usr/share/nginx/html
EXPOSE 80
