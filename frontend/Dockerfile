FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN chown -R node:node /app
USER node
EXPOSE 5173
CMD ["npm", "run", "dev"]
