FROM node:20-alpine

WORKDIR /app

# Install dependencies (including devDependencies for build)
COPY package.json package-lock.json ./
RUN npm ci

# Copy application files
COPY . .

# Generate Prisma client
RUN npx prisma generate

# Build the Next.js application for production
ENV NODE_ENV=production
RUN npm run build

# Expose port
EXPOSE 3000

# Start script (migrations then production server)
CMD npx prisma migrate deploy && npm start
