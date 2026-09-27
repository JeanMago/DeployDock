# ============================================
# DeployDock Frontend - Multi-stage Dockerfile
# ============================================

# --- Stage: Development ---
FROM node:20-alpine AS development

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

# --- Stage: Build ---
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# --- Stage: Production (Nginx) ---
FROM nginx:alpine AS production

# Copy custom Nginx config with API proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built SPA from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx runs on port 80 by default
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
