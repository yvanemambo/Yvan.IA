FROM node:22-bookworm-slim

ENV NODE_ENV=production
ENV GIVEMOTION_NO_GPU=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg ca-certificates unzip fontconfig fonts-liberation \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 libxshmfence1 libxfixes3 \
    libxkbcommon0 libpango-1.0-0 libcairo2 libatspi2.0-0 libdrm2 \
    && rm -rf /var/lib/apt/lists/*

COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund \
    && npx givemotion install

COPY server.mjs layout.mjs composition.mjs ./
EXPOSE 10000
CMD ["npm", "start"]
