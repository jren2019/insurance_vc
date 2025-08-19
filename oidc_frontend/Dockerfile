# Build stage only - no nginx needed
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Install Angular CLI globally
RUN npm install -g @angular/cli

# Copy source code
COPY . .

# Build the application (production)
RUN ng build --configuration production

# Create a simple stage to hold the built files
FROM alpine:latest

# Install a lightweight web server for health checks and coreutils for copy
RUN apk add --no-cache wget bash coreutils

# Stage built application to a non-mounted path
COPY --from=builder /app/dist/oidc_frontend/browser /opt/build

# Expose port (for health check)
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# On start, force-sync built files into the shared volume, then keep container alive
CMD bash -lc 'mkdir -p /usr/share/nginx/html && rm -rf /usr/share/nginx/html/* && cp -a /opt/build/. /usr/share/nginx/html/ && tail -f /dev/null' 