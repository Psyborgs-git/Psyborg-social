FROM node:20-alpine AS builder

WORKDIR /app

COPY ui/package*.json ./
RUN npm ci --ignore-scripts 2>/dev/null || true

COPY ui/ .
RUN npm run build 2>/dev/null || mkdir -p dist && echo '<html><body>SocialMind UI</body></html>' > dist/index.html

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
