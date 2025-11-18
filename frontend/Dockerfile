# Frontend Dockerfile for Development
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application files
COPY . .

# Expose Vite dev server port
EXPOSE 5174

# Set environment variables for Vite
ENV VITE_API_URL=http://localhost:8000

# Start development server
CMD ["npm", "start", "--", "--host", "0.0.0.0", "--port", "5174"]
