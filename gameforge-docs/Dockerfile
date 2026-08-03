# Build MkDocs site and serve with nginx (production docs host).
# Context: repository root
#   docker build -f gameforge-docs/Dockerfile --build-arg SITE_URL=https://docs.gameforge.website .

FROM python:3.12-slim AS builder

WORKDIR /docs

COPY gameforge-docs/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gameforge-docs/ .

ARG SITE_URL=https://docs.gameforge.website
RUN sed -i "s|^site_url:.*|site_url: ${SITE_URL}|" mkdocs.yml \
    && mkdocs build -f mkdocs.yml --strict

FROM nginx:1.27-alpine

COPY gameforge-docs/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /docs/site /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1
