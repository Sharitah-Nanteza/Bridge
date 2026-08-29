# Bridge Security Setup Guide

## Quick Start

### 1. Get Your Auth Token
When you start the app, it will print your token:
```
🔐 Bridge Auth Token: <your_token_here>
   Include this in Authorization header: 'Bearer {token}' for trusted-number/call-log API endpoints
```

**For production:** Add to `.env`:
```env
BRIDGE_AUTH_TOKEN=your_secure_token_here
```

### 2. Use the Secured Endpoints

#### List Trusted Numbers
```bash
curl https://your-bridge-url/api/calls/trusted \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Add a Trusted Number
```bash
curl -X POST https://your-bridge-url/api/calls/trusted \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "0771234567",
    "label": "Mom"
  }'
```

#### Remove a Trusted Number
```bash
curl -X DELETE https://your-bridge-url/api/calls/trusted/0771234567 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Get Recent Call Logs
```bash
curl https://your-bridge-url/api/calls/recent?limit=10 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Report a Scam (Now with Rate Limiting)

**Limit:** 5 reports per hour per IP  
**Duplicate Check:** 1 report per 24 hours for (number, reporter) pair

```bash
curl -X POST https://your-bridge-url/api/scams/report \
  -H "Content-Type: application/json" \
  -d '{
    "number": "0771234567",
    "reason": "Requesting PIN for airtel money",
    "reporter": "0700123456"
  }'
```

**If duplicate:**
```json
{
  "error": "This number was recently reported from your device. To prevent spam, duplicate reports are limited to once per 24 hours.",
  "duplicate": true
}
```

### 4. Query AI Assistant (Rate Limited)

**Limit:** 10 requests per 60 seconds per IP

```bash
curl -X POST https://your-bridge-url/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Someone asked for my PIN via SMS",
    "language": "en"
  }'
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/query` | 10 | 60 seconds |
| `/api/scams/report` | 5 | 60 minutes |
| `/ussd` | 30 | 60 seconds |
| `/api/calls/trusted` | Requires Bearer token | — |
| `/api/calls/recent` | Requires Bearer token | — |

---

## Error Responses

### Authentication Failed
```json
{
  "error": "Missing or invalid Authorization header",
  "status": 401
}
```

### Rate Limited
```json
{
  "error": "Rate limit exceeded: max 5 requests per 3600 seconds",
  "status": 429
}
```

### Duplicate Report
```json
{
  "error": "This number was recently reported from your device...",
  "duplicate": true,
  "status": 429
}
```

---

## Troubleshooting

**Q: I'm getting "Missing or invalid Authorization header"**  
A: Make sure you include `Authorization: Bearer <token>` in the request headers.

**Q: "Rate limit exceeded" error**  
A: Wait for the window to pass (60 seconds for queries, 1 hour for reports). Check if you're making multiple requests simultaneously.

**Q: "Duplicate report" when it's my first time**  
A: This could mean:
- A report from your IP was recently submitted (check your history)
- The (number, reporter) combination was reported in past 24h
- Different user from your IP already reported it

**Q: Exceptions showing in error messages**  
A: This is intentional for security. Check server logs (`stdout`) for debug info.

**Q: Token changes on restart**  
A: Set `BRIDGE_AUTH_TOKEN` in `.env` to persist the same token. Otherwise, a new random token is generated each startup.

---

## Integration Examples

### JavaScript (Web App)
```javascript
async function addTrustedNumber(number, label) {
  const token = prompt("Enter auth token:");
  const response = await fetch('/api/calls/trusted', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ number, label })
  });
  return response.json();
}
```

### Python
```python
import requests

TOKEN = "your_token_here"

def add_trusted_number(number, label=""):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.post(
        "http://localhost:5000/api/calls/trusted",
        json={"number": number, "label": label},
        headers=headers
    )
    return response.json()

def list_trusted():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(
        "http://localhost:5000/api/calls/trusted",
        headers=headers
    )
    return response.json()
```

### cURL with .env file
```bash
# Save token in .env, then:
source .env
curl https://your-bridge-url/api/calls/trusted \
  -H "Authorization: Bearer $BRIDGE_AUTH_TOKEN"
```

---

## What Changed

**Before:**  
- `/api/calls/trusted` endpoints were wide open — anyone could add/remove contacts
- `/api/scams/report` could be spam-reported infinitely
- Raw exceptions leaked to clients
- Paid API endpoints (query, USSD) had no rate limiting

**After:**  
- `/api/calls/trusted` requires Bearer token
- Reports limited to 5/hour + 1 per 24h per (number, reporter)
- Generic error messages to clients
- Query limited to 10/min, USSD to 30/min

See `SECURITY_FIXES.md` for full technical details.
