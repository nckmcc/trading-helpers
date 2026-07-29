# Trading Helpers API

Small persistent service for the Agentic Trading Account (v1.8.4).

## Endpoints

- `GET /health` — health check
- `POST /size/option` — calculate option position size
- `POST /size/equity` — calculate equity/ETF position size

## Deploy on Railway

1. Create a new project on Railway (or use an existing one).
2. Deploy from this folder (Dockerfile is included).
3. Railway will give you a public URL, e.g. `https://your-app.up.railway.app`.
4. Test: `curl https://your-app.up.railway.app/health`

## Example calls

### Option sizing
```bash
curl -X POST https://your-app.up.railway.app/size/option \
  -H "Content-Type: application/json" \
  -d '{
    "account_value": 500,
    "max_risk": 75,
    "premium_per_share": 0.65,
    "is_index_etf_exemption": false,
    "current_open_risk": 0
  }'
```

### Equity sizing
```bash
curl -X POST https://your-app.up.railway.app/size/equity \
  -H "Content-Type: application/json" \
  -d '{
    "account_value": 500,
    "max_risk": 75,
    "price": 185,
    "stop_price": 178,
    "current_open_risk": 0,
    "current_notional": 0,
    "allow_fractional": true
  }'
```
