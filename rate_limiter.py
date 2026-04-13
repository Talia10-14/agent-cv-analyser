"""
Rate limiter module - Prevent API abuse.
Uses Streamlit session state for simple in-memory rate limiting.
"""

import time
import streamlit as st
from typing import Tuple


class RateLimiter:
    """Simple rate limiter using session state."""
    
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def check(self, user_id: str = "default") -> Tuple[bool, str]:
        """
        Check if request is allowed.
        
        Args:
            user_id: Unique identifier for user/session
            
        Returns:
            Tuple of (is_allowed, message)
            - is_allowed: True if request allowed, False if rate limited
            - message: Status message or error message
        """
        # Initialize rate limits storage in session state
        if "rate_limits" not in st.session_state:
            st.session_state.rate_limits = {}
        
        now = time.time()
        
        # Initialize user if not exists
        if user_id not in st.session_state.rate_limits:
            st.session_state.rate_limits[user_id] = []
        
        # Clean old timestamps outside the window
        timestamps = st.session_state.rate_limits[user_id]
        timestamps = [t for t in timestamps if now - t < self.window_seconds]
        st.session_state.rate_limits[user_id] = timestamps
        
        # Check if limit reached
        if len(timestamps) >= self.max_requests:
            remaining = int(self.window_seconds - (now - timestamps[0]))
            msg = (
                f"⏱️ Rate limit reached ({self.max_requests} per {self.window_seconds}s). "
                f"Try again in {remaining}s"
            )
            return False, msg
        
        # Add new timestamp and allow request
        st.session_state.rate_limits[user_id].append(now)
        return True, "✓ Request allowed"
    
    def check_batch(self, count: int = 1, user_id: str = "default") -> Tuple[int, str]:
        """
        Check how many batch requests are allowed. Does not consume requests.
        
        Args:
            count: Number of requests to check
            user_id: Unique identifier for user/session
            
        Returns:
            Tuple of (allowed_count, message)
            - allowed_count: Number of requests that can be made
            - message: Status message
        """
        if "rate_limits" not in st.session_state:
            st.session_state.rate_limits = {}
        
        now = time.time()
        
        if user_id not in st.session_state.rate_limits:
            st.session_state.rate_limits[user_id] = []
        
        # Clean old timestamps
        timestamps = st.session_state.rate_limits[user_id]
        timestamps = [t for t in timestamps if now - t < self.window_seconds]
        st.session_state.rate_limits[user_id] = timestamps
        
        # Calculate available slots
        available = self.max_requests - len(timestamps)
        allowed_count = min(available, count)
        
        if allowed_count <= 0:
            remaining = int(self.window_seconds - (now - timestamps[0]))
            msg = f"Rate limit reached. Try again in {remaining}s"
            return 0, msg
        
        msg = f"Can process {allowed_count}/{count} request(s) ({self.max_requests - len(timestamps)} slots available)"
        return allowed_count, msg


# Global instance
limiter = RateLimiter(max_requests=5, window_seconds=60)
