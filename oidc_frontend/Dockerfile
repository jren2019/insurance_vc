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

# Build the application
RUN ng build

# Create a simple stage to hold the built files
FROM alpine:latest

# Install a lightweight web server for health checks
RUN apk add --no-cache wget

# Copy built application
COPY --from=builder /app/dist/oidc-frontend/browser /usr/share/nginx/html

# Expose port (for health check)
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Keep container running (nginx will serve the files from volume)
CMD ["tail", "-f", "/dev/null"] 