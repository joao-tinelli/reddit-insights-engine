# Build Stage
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package info and install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Set the production API URL during build time
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build for production
RUN npm run build

# Production Stage (Nginx)
FROM nginx:alpine

# Remove default nginx config and replace with ours
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/

# Copy built artifacts from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html


# Expose port 80
EXPOSE 80

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
