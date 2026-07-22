FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# SPA: cualquier ruta que no matchee un archivo cae a index.html (react-router).
# /api -> mismo origen que en dev (frontend/vite.config.ts), pega al
# servicio `api` de docker-compose y le saca el prefijo /api.
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    location /api/ {\n\
        proxy_pass http://api:8000/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
    }\n\
    location / {\n\
        try_files $uri /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf
