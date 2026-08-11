FROM node:24-alpine AS dependencies
WORKDIR /workspace
COPY package.json package-lock.json* ./
COPY apps/web/package.json ./apps/web/package.json
RUN npm install

FROM node:24-alpine AS builder
WORKDIR /workspace
COPY --from=dependencies /workspace/node_modules ./node_modules
COPY --from=dependencies /workspace/apps/web/node_modules ./apps/web/node_modules
COPY . .
RUN npm run build --workspace @athleteos/web

FROM node:24-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -S athleteos && adduser -S athleteos -G athleteos
COPY --from=builder /workspace/apps/web/.next ./.next
COPY --from=builder /workspace/apps/web/public ./public
COPY --from=builder /workspace/apps/web/package.json ./package.json
COPY --from=dependencies /workspace/node_modules ./node_modules
USER athleteos
EXPOSE 3000
CMD ["npm", "run", "start"]

