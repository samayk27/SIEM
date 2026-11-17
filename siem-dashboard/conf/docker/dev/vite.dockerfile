# ©AngelaMos | 2026
# vite.dockerfile

FROM node:25-alpine

RUN npm install --global pnpm@10.29.1

WORKDIR /app

ENV CI=true

EXPOSE 5173

CMD ["sh", "-c", "pnpm install && pnpm dev --host 0.0.0.0"]
