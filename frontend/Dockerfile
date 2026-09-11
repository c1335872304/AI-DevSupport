FROM node:20-alpine AS build

WORKDIR /app
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY packages ./packages
COPY build ./build
COPY public ./public
COPY index.html vite.config.ts tsconfig.json uno.config.ts eslint.config.js .env.prod ./

RUN corepack enable && pnpm install --frozen-lockfile

# Keep dependency installation cacheable when only application source changes.
COPY src ./src
RUN pnpm build

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
