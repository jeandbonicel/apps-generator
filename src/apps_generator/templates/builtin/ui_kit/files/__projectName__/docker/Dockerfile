FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .npmrc* ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build-storybook

FROM nginx:alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/storybook-static /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
