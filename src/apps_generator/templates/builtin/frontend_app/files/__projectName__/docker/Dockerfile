FROM node:{{ nodeVersion }}-alpine AS builder
{% if packageManager == "pnpm" %}
RUN corepack enable && corepack prepare pnpm@latest --activate
{% endif %}
WORKDIR /app
COPY package*.json {% if packageManager == "pnpm" %}pnpm-lock.yaml* {% endif %}./
COPY local-deps/ ./local-deps/
RUN {{ packageManager }} install
COPY . .
RUN {{ packageManager }} run build

FROM nginx:alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
