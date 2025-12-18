FROM node:20-alpine AS base
RUN apk add --no-cache libc6-compat

FROM base AS deps
WORKDIR /src
COPY package*.json ./
RUN npm ci

FROM base AS builder
WORKDIR /src
COPY --from=deps /src/node_modules ./node_modules
COPY . .
RUN npx prisma generate
ENV NODE_ENV=production
RUN npm run build

FROM base AS runner
WORKDIR /src
ENV NODE_ENV=production
ENV PORT=3001

# Copy standalone output + static files
COPY --from=builder /src/.next/standalone ./
COPY --from=builder /src/.next/static ./.next/static

# Copy all node_modules (needed for prisma CLI and seed script)
COPY --from=builder /src/node_modules ./node_modules
COPY --from=builder /src/prisma ./prisma
COPY --from=builder /src/scripts ./scripts
COPY --from=builder /src/package.json ./package.json

EXPOSE 3001

# Run migrations, then start with node (not npm start)
# Seeding is skipped in production - data already exists from initial setup
CMD ./node_modules/.bin/prisma migrate deploy && node server.js
