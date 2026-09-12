# Production image for the Next.js frontend. Built and run by
# docker-compose.prod.yml (locally or on the Hostinger VPS) and by the
# GitHub Actions deploy workflows — see docs/deploying-to-hostinger.pdf for
# the full walkthrough.
#
# NEXT_PUBLIC_API_URL is a build-time value (Next.js inlines every
# NEXT_PUBLIC_* variable into the compiled JS), so the test and production
# images CANNOT share one build — each environment passes its own
# --build-arg NEXT_PUBLIC_API_URL so the frontend calls its own backend and
# the auth cookies stay same-site (see CLAUDE.md's hostname-matching
# gotcha).

FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
# Set only for the test deployment, so a banner warns people they're not on
# the real production site — see src/lib/config.ts / src/app/layout.tsx.
ARG NEXT_PUBLIC_ENVIRONMENT_LABEL
ENV NEXT_PUBLIC_ENVIRONMENT_LABEL=${NEXT_PUBLIC_ENVIRONMENT_LABEL}
RUN npm run build

# Final, minimal runtime image: only the standalone server output (see
# output: "standalone" in next.config.ts) plus static/public assets — no
# node_modules install needed at runtime.
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
