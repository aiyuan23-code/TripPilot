FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/index.html ./index.html
COPY frontend/tsconfig*.json ./
COPY frontend/vite.config.ts ./vite.config.ts
COPY frontend/src ./src

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_AMAP_JS_KEY
ARG VITE_AMAP_SERVICE_HOST=/_AMapService
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_AMAP_JS_KEY=${VITE_AMAP_JS_KEY} \
    VITE_AMAP_SERVICE_HOST=${VITE_AMAP_SERVICE_HOST}

RUN npm run build

FROM nginx:1.28-alpine

COPY deploy/docker/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
