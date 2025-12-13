FROM node:20-alpine

WORKDIR /app

# Install dependencies (including devDependencies for build)
COPY package.json package-lock.json* ./
RUN npm install

# Copy application files
COPY . .

# Generate Prisma client
RUN npx prisma generate

# Build the Next.js application for production
ENV NODE_ENV=production
RUN npm run build

# Expose port
EXPOSE 3001

# Start script (migrations, seeding, then production server)
# Seeding is idempotent - safe to run on every startup
CMD npx prisma migrate deploy && npx prisma db seed && npm start
