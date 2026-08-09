# Node.js 22 tabanlı Docker imajı
FROM node:22-alpine AS builder

WORKDIR /app

# Bağımlılık tanımlarını kopyala
COPY package.json package-lock.json* ./

# Bağımlılıkları kur
RUN npm ci

# Uygulama kodunu kopyala
COPY . .

# Next.js uygulamasını derle
RUN npm run build

# Çalışma zamanı imajı
FROM node:22-alpine AS runner

WORKDIR /app

# Gerekli dosyaları kopyala
COPY --from=builder /app/package.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start"]
