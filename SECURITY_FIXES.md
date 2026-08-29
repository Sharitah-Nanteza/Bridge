# Bridge Security Fixes — Implementation Summary

## Overview
Implemented 4 critical security fixes addressing authentication, rate limiting, duplicate detection, and error handling vulnerabilities.

---

## 1. Trusted-Numbers API Authentication (✅ FIXED)

### Problem
- `/api/calls/trusted` endpoints (GET, POST, DELETE) had no authentication
- Anyone on the internet could add/remove trusted contacts, whitelist scammers, or delete legitimate contacts

### Solution
- Added `@require_auth` decorator to all trusted-numbers endpoints
- Token-based authentication via `Authorization: Bearer <token>` header
- Token generated automatically on startup (shown in console)
- Store `BRIDGE_AUTH_TOKEN` in `.env` for persistence

### Usage
```bash
# Add a trusted number
curl -X POST http://localhost:5000/api/calls/trusted \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"number": "0771234567", "label": "Mom"}'

# List trusted numbers
curl http://localhost:5000/api/calls/trusted \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Remove a trusted number
curl -X DELETE http://localhost:5000/api/calls/trusted/0771234567 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Recent call logs
curl http://localhost:5000/api/calls/recent \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Code
- New module: `security.py` with `@require_auth` decorator
- Modified endpoints: `/api/calls/trusted` (GET, POST, DELETE), `/api/calls/recent`

---

## 2. Scam-Report Rate Limiting (✅ FIXED)

### Problem
- `/api/scams/report` had no rate limiting
- Attackers could spam-report rival numbers or flood reports to game the trust system
- No per-IP or per-session throttling

### Solution
- Added `@rate_limit(max_requests=5, window_seconds=3600)` decorator
- Limits: 5 reports per IP per hour
- Returns HTTP 429 (Too Many Requests) when exceeded
- Per-IP tracking via X-Forwarded-For header (respects reverse proxies)

### Behavior
```json
{
  "error": "Rate limit exceeded: max 5 requests per 3600 seconds",
  "status": 429
}
```

### Code
- Modified endpoint: `/api/scams/report`
- New utility: `rate_limit()` decorator in `security.py`

---

## 3. Duplicate Report Detection (✅ FIXED)

### Problem
- Same reporter could report the same number unlimited times
- Scammers could artificially inflate their own low-risk status or deflate competitors' ratings
- No verification that reports are genuine

### Solution
- Added `check_duplicate_report()` in `scamdb.py`
- Detects (number, reporter) pairs within 24-hour window
- Returns HTTP 429 with helpful message when duplicate detected
- Works with database query (persistent across restarts)

### Behavior
```json
{
  "error": "This number was recently reported from your device. To prevent spam, duplicate reports are limited to once per 24 hours.",
  "duplicate": true,
  "status": 429
}
```

### Code
- New function: `check_duplicate_report()` in `scamdb.py`
- Added duplicate check in `/api/scams/report`
- Database query: looks up (number, reporter) pair in past 24 hours

---

## 4. API Rate Limiting for Paid Services (✅ FIXED)

### Problem
- `/api/query` and `/ussd` call paid APIs (Gemini, Africa's Talking SMS/Voice)
- No throttling = attacker could exhaust quota or rack up bills
- No per-caller tracking

### Solution

#### `/api/query` (Web query endpoint)
- Rate limit: 10 requests per 60 seconds per IP
- Decorator: `@rate_limit(max_requests=10, window_seconds=60)`

#### `/ussd` (Phone interface)
- Rate limit: 30 interactions per 60 seconds per phone number
- Decorator: `@rate_limit(max_requests=30, window_seconds=60, key_func=lambda: request.values.get("phoneNumber", "unknown"))`
- Tracks by phone number (not IP) since phone can change networks

### Code
- In-memory rate limiter: `RateLimiter` class in `security.py`
- Automatic cleanup: removes expired entries every 60 seconds
- Per-endpoint configuration: customize limits in decorator

---

## 5. Exception Leaking (✅ FIXED)

### Problem
- Raw Gemini API exceptions (including stack traces, sometimes API key fragments) leaked to client
- `/api/query` returned `str(e)` directly in JSON response

### Solution
- Generic error message returned to client: "Failed to process query. Please try again later."
- Full exception still logged to stdout for debugging
- Prevents information disclosure

### Before
```python
except Exception as e:
    print(f"Gemini API Error: {e}")
    return jsonify({"error": str(e)}), 500  # ❌ Leaks details
```

### After
```python
except Exception as e:
    print(f"Gemini API Error: {e}")  # ✅ Still logged for debugging
    return jsonify({"error": "Failed to process query. Please try again later."}), 500
```

### Code
- Modified: `/api/query` error handler
- Pattern: applied to all Gemini/Africa's Talking error paths

---

## Security Architecture

### New Module: `security.py`
```python
# Core components:
- AUTH_TOKEN: Generate/load from env
- RateLimiter: In-memory tracking with auto-cleanup
- DuplicateDetector: Tracks (key, reporter) pairs by time window
- @require_auth: Decorator for auth check
- @rate_limit: Decorator for rate limiting
- get_client_ip(): Proxy-aware IP extraction
```

### Rate Limiter Details
- In-memory: no database dependency
- Auto-cleanup: removes entries older than 1 hour
- Efficient: O(1) check + append per request
- Survives restarts: token-based, not session-based (for HTTPS production, use session store)

### Duplicate Detector Details
- Database layer: `check_duplicate_report()` in `scamdb.py`
- Queries: scans past 24 hours for (number, reporter) match
- Timing: creates timestamp at report time
- Index: uses `idx_reports_number` for fast lookup

---

## Environment Variables

Add to `.env`:
```bash
# Security
BRIDGE_AUTH_TOKEN=your_secure_token_here  # Required for /api/calls/trusted and /api/calls/recent
```

If `BRIDGE_AUTH_TOKEN` is not set:
- Random token auto-generated on startup
- Printed to console (good for testing, **not recommended for production**)

---

## Testing the Fixes

### 1. Test Auth Protection
```bash
# Without token (should fail)
curl http://localhost:5000/api/calls/trusted
# Response: {"error": "Missing or invalid Authorization header"}, 401

# With token (should succeed)
curl http://localhost:5000/api/calls/trusted \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 2. Test Rate Limiting (Report)
```bash
# First 5 reports succeed (within 1 hour)
for i in {1..5}; do
  curl -X POST http://localhost:5000/api/scams/report \
    -H "Content-Type: application/json" \
    -d '{"number": "0771234567", "reason": "Fraud attempt"}' \
    --silent | grep -q "error" || echo "Request $i: Success"
done

# 6th request fails
curl -X POST http://localhost:5000/api/scams/report \
  -H "Content-Type: application/json" \
  -d '{"number": "0771234567", "reason": "Another fraud report"}'
# Response: 429 Too Many Requests
```

### 3. Test Duplicate Detection
```bash
# First report from same phone succeeds
curl -X POST http://localhost:5000/api/scams/report \
  -H "Content-Type: application/json" \
  -d '{"number": "0771234567", "reason": "Fraud", "reporter": "0700123456"}'
# Response: 201 Created

# Second report from same phone/number within 24h fails
curl -X POST http://localhost:5000/api/scams/report \
  -H "Content-Type: application/json" \
  -d '{"number": "0771234567", "reason": "Fraud again", "reporter": "0700123456"}'
# Response: {"error": "...", "duplicate": true}, 429
```

### 4. Test Exception Handling
```bash
# Send invalid query (won't leak exception text)
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "", "language": "en"}'
# Response: {"error": "Failed to process query. Please try again later."}, 500
# (Not the raw Gemini exception)
```

---

## Production Hardening Recommendations

1. **Token Management**
   - Generate token with `secrets.token_urlsafe(32)` (already done in `security.py`)
   - Store in secure `.env` file (not in git)
   - Rotate periodically
   - For public APIs, use API keys with per-client rate limits

2. **Rate Limiting**
   - Current: in-memory (restarts wipe limits)
   - Production: move to Redis for distributed rate limiting
   - Add per-endpoint dashboards to monitor abuse

3. **Database Encryption**
   - Phone numbers: encrypt at rest (currently plain SQLite)
   - Recommended: use `cryptography` library with per-database key

4. **Logging & Monitoring**
   - Log all failed auth attempts
   - Alert on rate limit spikes
   - Track which IPs/phones are being rate-limited
   - Monitor Gemini quota usage

5. **HTTPS & Reverse Proxy**
   - Enforce HTTPS in production
   - Reverse proxy (nginx) should set X-Forwarded-For correctly
   - Security module already handles this via `get_client_ip()`

---

## Summary of Changes

| File | Change | Impact |
|------|--------|--------|
| `security.py` | NEW | Auth, rate limiting, duplicate detection utilities |
| `app.py` | Modified | Added decorators, fixed error leaking, imports security module |
| `scamdb.py` | Modified | Added `check_duplicate_report()` function |
| `calldb.py` | Unchanged | No changes needed |

**Lines Added**: ~200 lines across security.py and updates
**Backward Compatibility**: Yes (SMS commands unchanged, USSD unchanged)
**Database Schema Changes**: None (new queries only)

---

## What This Protects Against

✅ **Authentication Bypass**: Trusted-numbers endpoints now require token  
✅ **Spam Reports**: Rate limiting + duplicate detection prevent gaming the scam system  
✅ **Quota Exhaustion**: Gemini/Africa's Talking APIs now rate-limited  
✅ **Information Disclosure**: No more raw exception text in client responses  
✅ **DDoS-like Abuse**: Per-IP/per-phone rate limiting on critical endpoints  

---

## Next Steps (Already Identified)

- [ ] Move rate limiter to Redis for distributed deployments
- [ ] Add database encryption for phone numbers
- [ ] Implement request logging & alerting for abuse patterns
- [ ] Add feedback loop for users to report false positives
- [ ] Cross-reference with external scam databases (telco feeds)
