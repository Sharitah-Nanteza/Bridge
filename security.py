"""
Security utilities for Bridge: authentication, rate limiting, duplicate detection.
"""
import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from functools import wraps
from flask import request, jsonify

# Load or generate owner auth token (should be stored in .env or database in production)
AUTH_TOKEN = os.getenv("BRIDGE_AUTH_TOKEN", "")
if not AUTH_TOKEN:
    # Generate a random token if none provided
    AUTH_TOKEN = secrets.token_urlsafe(32)
    print(f"⚠️  Generated temporary auth token: {AUTH_TOKEN}")
    print("   Set BRIDGE_AUTH_TOKEN in your .env file to persist across restarts")


class RateLimiter:
    """Simple in-memory rate limiter with per-key tracking."""
    
    def __init__(self):
        self.requests = defaultdict(list)  # key -> list of (timestamp, count)
        self.last_cleanup = time.time()
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if a key has exceeded rate limit.
        Returns True if allowed, False if exceeded.
        """
        now = time.time()
        
        # Cleanup old entries every 100 checks to prevent unbounded memory growth
        if now - self.last_cleanup > 60:
            self._cleanup_old_entries(now)
            self.last_cleanup = now
        
        window_start = now - window_seconds
        request_times = self.requests[key]
        
        # Remove requests outside the window
        request_times[:] = [ts for ts in request_times if ts > window_start]
        
        if len(request_times) >= max_requests:
            return False
        
        request_times.append(now)
        return True
    
    def _cleanup_old_entries(self, now: float):
        """Remove keys with no recent activity."""
        keys_to_delete = [
            key for key, timestamps in self.requests.items()
            if not timestamps or (now - timestamps[-1]) > 3600
        ]
        for key in keys_to_delete:
            del self.requests[key]


class DuplicateDetector:
    """Detect duplicate reports from the same source within a time window."""
    
    def __init__(self):
        self.reports = defaultdict(list)  # (number, reporter) -> list of timestamps
        self.last_cleanup = time.time()
    
    def is_duplicate(self, number: str, reporter: str = None, window_hours: int = 24) -> bool:
        """
        Check if this (number, reporter) pair has been reported recently.
        Returns True if duplicate found, False if new report.
        """
        now = time.time()
        
        # Cleanup every 100 checks
        if now - self.last_cleanup > 60:
            self._cleanup_old_entries(now)
            self.last_cleanup = now
        
        key = (number, reporter)
        window_start = now - (window_hours * 3600)
        timestamps = self.reports[key]
        
        # Remove old reports outside the window
        timestamps[:] = [ts for ts in timestamps if ts > window_start]
        
        is_dup = len(timestamps) > 0
        timestamps.append(now)
        return is_dup
    
    def _cleanup_old_entries(self, now: float):
        """Remove keys with no recent activity."""
        keys_to_delete = [
            key for key, timestamps in self.reports.items()
            if not timestamps or (now - timestamps[-1]) > (24 * 3600)
        ]
        for key in keys_to_delete:
            del self.reports[key]


# Global instances
rate_limiter = RateLimiter()
duplicate_detector = DuplicateDetector()


def verify_auth_token():
    """
    Extract and verify auth token from request headers.
    Token must be provided as: Authorization: Bearer <token>
    
    Returns (is_valid: bool, error_message: str or None)
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False, "Missing or invalid Authorization header"
    
    token = auth_header[7:].strip()  # Remove "Bearer "
    if not token:
        return False, "Authorization token is empty"
    
    if token != AUTH_TOKEN:
        return False, "Invalid authorization token"
    
    return True, None


def require_auth(f):
    """Decorator to protect endpoints with auth token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_valid, error_msg = verify_auth_token()
        if not is_valid:
            return jsonify({"error": error_msg or "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(max_requests: int, window_seconds: int, key_func=None):
    """
    Decorator for rate limiting.
    key_func: callable(request) -> str, defaults to client IP
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Default to IP-based rate limiting
            if key_func:
                key = key_func()
            else:
                key = request.remote_addr or "unknown"
            
            if not rate_limiter.is_allowed(key, max_requests, window_seconds):
                return jsonify({
                    "error": f"Rate limit exceeded: max {max_requests} requests per {window_seconds} seconds"
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_client_ip() -> str:
    """Get client IP, considering X-Forwarded-For in case of reverse proxy."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "unknown"
