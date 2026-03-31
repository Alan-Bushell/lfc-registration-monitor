# Stage 1: Build Frontend
FROM node:18-alpine as frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Production Backend + Static Files
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend static files
COPY --from=frontend-builder /frontend/dist /app/app/static

# Environment Variables (can be overridden at runtime)
ENV PORT=8080
ENV FRONTEND_URL="https://YOUR_CLOUD_RUN_URL"
ENV DATABASE_URL=""

# Expose port (Cloud Run uses 8080 by default)
EXPOSE 8080

# Command to run the application
# Use shell form to expand env vars properly
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}