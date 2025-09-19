FROM node:18

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Create output and tmp directories (for local/shared output)
RUN mkdir -p /app/output/clips /app/tmp

# Default command (can be overridden)
CMD ["npx", "ts-node", "src/cli.ts"]
