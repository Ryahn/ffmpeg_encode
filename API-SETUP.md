# Stats API Setup Guide

## Overview

A new Node.js/Express API backend has been added to collect and serve encoding statistics from the ffmpeg_encode desktop app. Stats are displayed publicly on the website.

## What's New

### Files Created
- `backend/server.js` — Express API server with 3 endpoints
- `backend/package.json` — Node dependencies
- `backend/db.js` — PostgreSQL database client and initialization
- `backend/Dockerfile` — Docker container definition
- `backend/README.md` — API documentation
- `backend/test-api.js` — Test script
- `backend/.env.example` — Environment variable template
- `.gitignore` — Excludes node_modules and sensitive files

### Files Modified
- `docker-compose.yml` — Added stats-api service
- `config/Caddy/Caddyfile` — Added `/api/*` routing
- `.env` — Added JWT_SECRET and APP_KEY
- `index.html` — Added stats display section
- `assets/css/styles.css` — Added stats styling
- `assets/js/main.js` — Added stats fetching logic

## API Endpoints

### 1. Authentication
```
POST /api/auth/token
{
  "app_key": "ffmpeg-encode-app-secret-key"
}
→ Returns JWT token valid for 24 hours
```

### 2. Submit Stats (requires JWT)
```
POST /api/stats
Authorization: Bearer <token>
{
  "files_encoded": 13,
  "total_output_size_bytes": 7673756992,
  "total_encoding_time_seconds": 2343.4
}
```

### 3. Get Stats (public)
```
GET /api/stats
→ Returns current stats (no auth required)
```

## Quick Start (Docker)

```bash
# Update environment variables in .env
# Then deploy:
docker-compose down  # If running
docker-compose up -d

# Check logs
docker-compose logs stats-api

# Verify the API is running
curl http://localhost:3001/api/health
```

## Testing Locally (Without Docker)

```bash
cd backend
npm install
npm start

# In another terminal:
node test-api.js http://localhost:3001
```

## Integration with Desktop App (Python Example)

```python
import requests

class StatSubmitter:
    def __init__(self, api_url="https://ffmpeg-encode.com"):
        self.api_url = api_url
        self.token = None
        self.authenticate()

    def authenticate(self):
        """Get JWT token from API"""
        response = requests.post(
            f"{self.api_url}/api/auth/token",
            json={"app_key": "ffmpeg-encode-app-secret-key"}
        )
        self.token = response.json()['access_token']

    def submit_stats(self, files_encoded, output_size_bytes, encoding_time_seconds):
        """Submit encoding statistics"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.api_url}/api/stats",
            json={
                "files_encoded": files_encoded,
                "total_output_size_bytes": output_size_bytes,
                "total_encoding_time_seconds": encoding_time_seconds
            },
            headers=headers
        )
        return response.json()

# Usage in your app:
submitter = StatSubmitter()
submitter.submit_stats(
    files_encoded=13,
    output_size_bytes=7673756992,  # 7.15 GB
    encoding_time_seconds=2343.4  # ~39 minutes
)
```

## Database

The API uses Umami's existing PostgreSQL database. A new table `app_stats` is created automatically on first run.

**Schema:**
```sql
CREATE TABLE app_stats (
  id SERIAL PRIMARY KEY,
  files_encoded INTEGER DEFAULT 0,
  total_output_size_bytes BIGINT DEFAULT 0,
  total_encoding_time_seconds DECIMAL(10, 2) DEFAULT 0,
  updated_at TIMESTAMP DEFAULT NOW()
)
```

## Website Display

The stats section appears before the footer with:
- Total files encoded
- Total output size (formatted as GB, MB, etc.)
- Total encoding time (formatted as Xh Ym Zs)

Stats update when the page is refreshed (on-demand).

## Security

- **JWT Secret**: Stored in `.env`, signing key for tokens
- **App Key**: Shared secret used to request tokens
- **Public Endpoint**: `/api/stats` has no authentication (stats are public)
- **Authenticated Endpoint**: `/api/stats` POST requires valid JWT
- **Token Expiry**: 24 hours (can be changed in server.js)

⚠️ **Change defaults before production:**
- Update `JWT_SECRET` in `.env`
- Update `APP_KEY` in `.env`

## Troubleshooting

### API doesn't respond
```bash
# Check if backend container is running
docker-compose ps stats-api

# Check logs
docker-compose logs stats-api
```

### Database connection error
- Verify `POSTGRES_PASSWORD` matches `.env`
- Ensure Umami database is running: `docker-compose logs umami-db`
- Check if table exists: Connect to PostgreSQL and run:
  ```sql
  SELECT * FROM app_stats;
  ```

### Invalid token error
- Token may have expired (24-hour expiry)
- Request a new token with `/api/auth/token`
- Verify APP_KEY is correct

### Stats not showing on website
- Open browser console (F12) and check for errors
- Verify `/api/stats` endpoint is working: `curl http://localhost:3001/api/stats`
- Ensure Caddy is routing `/api/*` correctly

## Next Steps

1. ✅ Deploy backend to production
2. ✅ Test API endpoints with `backend/test-api.js`
3. ✅ Integrate desktop app to submit stats
4. ✅ Monitor stats section on website

See `backend/README.md` for detailed API documentation and `backend/.env.example` for all configuration options.
