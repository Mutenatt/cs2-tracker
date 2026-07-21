FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --omit=dev
COPY src ./src
# Dentro del contenedor hay que escuchar en 0.0.0.0 para que el port mapping
# (publicado solo en 127.0.0.1 del host) funcione.
ENV GC_SIDECAR_HOST=0.0.0.0
CMD ["node", "src/index.js"]
