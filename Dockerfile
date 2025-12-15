# Build Frontend
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Setup Backend
FROM python:3.10-slim
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy frontend build to a static dir (optional, if serving from FastAPI)
# For now, we'll just keep them separate or assume a reverse proxy.
# But let's copy it to be safe if we want to serve it.
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Expose port
EXPOSE 8000

# Run FastAPI
# Run FastAPI
CMD sh -c "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"
