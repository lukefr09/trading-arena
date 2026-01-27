# Cloudflare Setup Guide

## Prerequisites
- Cloudflare account
- Wrangler CLI installed (`npm install -g wrangler`)
- Node.js 18+

## 1. Authenticate Wrangler

```bash
wrangler login
```

## 2. Create D1 Database

```bash
cd cloudflare/api

# Create database
wrangler d1 create trading-arena

# Note the database_id from output and update wrangler.toml
```

Update `wrangler.toml`:
```toml
[[d1_databases]]
binding = "DB"
database_name = "trading-arena"
database_id = "YOUR_DATABASE_ID"  # <-- Replace this
```

## 3. Initialize Database Schema

```bash
# Apply schema to local dev database
wrangler d1 execute trading-arena --local --file=../schema.sql

# Apply schema to production
wrangler d1 execute trading-arena --file=../schema.sql
```

## 4. Set API Key Secret

```bash
# Generate a secure API key
API_KEY=$(openssl rand -hex 32)
echo "Your API key: $API_KEY"

# Set it as a secret
wrangler secret put API_KEY
# Paste the key when prompted
```

Save this API key - you'll need it for the orchestrator!

## 5. Deploy Workers API

```bash
cd cloudflare/api

# Install dependencies
npm install

# Deploy
wrangler deploy
```

Note the worker URL (e.g., `https://trading-arena-api.YOUR_SUBDOMAIN.workers.dev`)

## 6. Deploy Dashboard to Pages

```bash
cd dashboard

# Install dependencies
npm install

# Build
npm run build

# Create Pages project
wrangler pages project create trading-arena-dashboard

# Deploy
wrangler pages deploy dist
```

Or connect to GitHub for automatic deployments:
1. Go to Cloudflare Dashboard > Pages
2. Create a project > Connect to Git
3. Select your repository
4. Set build command: `cd dashboard && npm install && npm run build`
5. Set output directory: `dashboard/dist`

## 7. Set Environment Variables for Dashboard

In Cloudflare Pages settings, add:
- `VITE_API_URL`: Your Workers API URL
- `VITE_WS_URL`: Your Workers WebSocket URL (same as API but with `wss://` and `/ws`)

## 8. Configure CORS (if needed)

The API already allows all origins. For production, update `cloudflare/api/src/index.ts`:
```typescript
app.use('*', cors({
  origin: 'https://your-dashboard-url.pages.dev',
  // ...
}));
```

## 9. Test the Setup

```bash
# Test API health
curl https://trading-arena-api.YOUR_SUBDOMAIN.workers.dev/

# Test state endpoint
curl https://trading-arena-api.YOUR_SUBDOMAIN.workers.dev/api/state
```

## Environment Variables Summary

### VPS (.env)
```
CF_API_URL=https://trading-arena-api.YOUR_SUBDOMAIN.workers.dev
CF_API_KEY=your-generated-api-key
FINNHUB_API_KEY=your-finnhub-key
```

### Cloudflare Workers (secrets)
```
API_KEY=your-generated-api-key
```

### Cloudflare Pages (environment variables)
```
VITE_API_URL=https://trading-arena-api.YOUR_SUBDOMAIN.workers.dev
VITE_WS_URL=wss://trading-arena-api.YOUR_SUBDOMAIN.workers.dev/ws
```
