# Build the static app with Node, then serve it with Nginx (which also proxies /api).
FROM node:24-slim AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build


FROM nginx:stable-alpine

COPY nginx/ /etc/nginx/
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost/healthz >/dev/null || exit 1
