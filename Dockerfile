FROM nginx:1.27-alpine

# The web edition is a dependency-free Canvas game, so the image has no build
# step, Python runtime, or external CDN dependency.
COPY web/ /usr/share/nginx/html/
COPY favicon.png /usr/share/nginx/html/favicon.png

EXPOSE 80
