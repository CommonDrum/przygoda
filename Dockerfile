# Stage 1: Build frontend
FROM node:22-alpine AS frontend
WORKDIR /build
RUN npm install -g bun
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ .
RUN bun run build

# Stage 2: Backend
FROM python:3.12-slim AS backend
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
RUN rm -f .env przygoda.db
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Nginx with frontend static files
FROM nginx:alpine AS nginx
COPY --from=frontend /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
