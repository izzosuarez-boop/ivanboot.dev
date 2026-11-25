# Multi-stage build for the Next.js app (portfolio + store), using standalone output.
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Public, build-time values (inlined into the client bundle). No secrets here.
ARG NEXT_PUBLIC_STORE_BASE=""
ARG NEXT_PUBLIC_STORE_PASSWORD=""
# Domains and hiring profiles of the two portfolio versions (sites.env on the server): the pages are prerendered
# with them. Server-side only, never in the client bundle.
ARG UPWORK_SITE_HOST="" UPWORK_STORE_HOST="" UPWORK_PROFILE_URL="" WORKANA_SITE_HOST="" WORKANA_STORE_HOST="" WORKANA_PROFILE_URL=""
ENV NEXT_PUBLIC_STORE_BASE=$NEXT_PUBLIC_STORE_BASE \
    NEXT_PUBLIC_STORE_PASSWORD=$NEXT_PUBLIC_STORE_PASSWORD \
    UPWORK_SITE_HOST=$UPWORK_SITE_HOST UPWORK_STORE_HOST=$UPWORK_STORE_HOST UPWORK_PROFILE_URL=$UPWORK_PROFILE_URL \
    WORKANA_SITE_HOST=$WORKANA_SITE_HOST WORKANA_STORE_HOST=$WORKANA_STORE_HOST WORKANA_PROFILE_URL=$WORKANA_PROFILE_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:24-alpine AS run
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S -g 10001 web && adduser -S -u 10001 -G web web
COPY --from=build --chown=web:web /app/.next/standalone ./
COPY --from=build --chown=web:web /app/.next/static ./.next/static
COPY --from=build --chown=web:web /app/public ./public
USER web
EXPOSE 3000
CMD ["node", "server.js"]
