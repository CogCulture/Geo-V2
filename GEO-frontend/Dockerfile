# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Define build arguments
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID
ARG NEXT_PUBLIC_RAZORPAY_KEY_ID

# Set them as environment variables so Next.js sees them during build
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV NEXT_PUBLIC_RAZORPAY_KEY_ID=$NEXT_PUBLIC_RAZORPAY_KEY_ID

# Install dependencies
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Run
FROM node:20-alpine

WORKDIR /app

# Copy production artifacts from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/postcss.config.js ./
COPY --from=builder /app/tailwind.config.ts ./

EXPOSE 3000

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

CMD ["npm", "start"]
