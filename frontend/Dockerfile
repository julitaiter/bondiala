FROM node:22-bookworm-slim AS build
WORKDIR /app/frontend
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY assets/ /app/assets/
RUN npm run build

FROM node:22-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
RUN groupadd --gid 10001 bondiala && useradd --uid 10001 --gid bondiala --create-home bondiala
COPY --from=build --chown=bondiala:bondiala /app/frontend/.next/standalone ./
COPY --from=build --chown=bondiala:bondiala /app/frontend/.next/static ./.next/static
COPY --from=build --chown=bondiala:bondiala /app/frontend/public ./public
USER bondiala
EXPOSE 3000
CMD ["node", "server.js"]
