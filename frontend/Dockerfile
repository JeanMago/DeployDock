# ============================================
# DeployDock Frontend - Multi-stage Dockerfile
# ============================================

# --- Stage: Development ---
FROM node:20-alpine AS development
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

# --- Stage: Build ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
# Se dist ja foi compilado localmente em alta velocidade, reutiliza; senao executa vite build direto sem typecheck pesado
RUN if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then npx vite build; fi

# --- Stage: Production (Nginx) ---
FROM nginx:alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
