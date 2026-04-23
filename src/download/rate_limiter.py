#!/usr/bin/env python3
"""
Rate limiting module to comply with NCBI/PubMed policies.

Official policy: https://www.ncbi.nlm.nih.gov/books/NBK25497/
- Without API Key: max 3 requests/second
- With API Key: max 10 requests/second
- Off-peak hours (weekends, 9pm-5am EST): more flexible limits
"""

import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


class RateLimiter:
    """
    Rate limiting manager that complies with NCBI policies.

    Uses token bucket algorithm for precise rate control.
    """

    def __init__(
        self,
        requests_per_second: float = 3.0,
        requests_per_second_off_peak: float = 10.0,
        min_delay: float = 0.34,
        min_delay_off_peak: float = 0.1,
    ):
        """
        Initialize the rate limiter.

        Args:
            requests_per_second: Requests allowed per second (peak hours)
            requests_per_second_off_peak: Requests in off-peak hours
            min_delay: Minimum delay between requests (seconds)
            min_delay_off_peak: Minimum delay in off-peak
        """
        self.requests_per_second = requests_per_second
        self.requests_per_second_off_peak = requests_per_second_off_peak
        self.min_delay = min_delay
        self.min_delay_off_peak = min_delay_off_peak

        # Internal state
        self.last_request_time: Optional[float] = None
        self.request_count = 0
        self.total_wait_time = 0.0

        # EST timezone to detect off-peak hours
        self.est_tz = ZoneInfo("US/Eastern")

    def is_off_peak_hours(self) -> bool:
        """
        Detect whether we are in NCBI off-peak hours.

        Off-peak: Weekends or between 9pm-5am EST on weekdays.

        Returns:
            True if we are in off-peak hours
        """
        now_est = datetime.now(self.est_tz)

        # Weekend (Saturday=5, Sunday=6)
        if now_est.weekday() in [5, 6]:
            return True

        # Between 9pm (21:00) and 5am (05:00)
        hour = now_est.hour
        if hour >= 21 or hour < 5:
            return True

        return False

    def wait_if_needed(self) -> float:
        """
        Wait the time required to comply with the rate limit.

        Returns:
            Time waited in seconds
        """
        if self.last_request_time is None:
            self.last_request_time = time.time()
            self.request_count += 1
            return 0.0

        # Determine delay based on schedule
        if self.is_off_peak_hours():
            min_delay = self.min_delay_off_peak
        else:
            min_delay = self.min_delay

        # Compute time since last request
        elapsed = time.time() - self.last_request_time

        # Wait if not enough time has passed
        if elapsed < min_delay:
            wait_time = min_delay - elapsed
            time.sleep(wait_time)
            self.total_wait_time += wait_time
        else:
            wait_time = 0.0

        # Update state
        self.last_request_time = time.time()
        self.request_count += 1

        return wait_time

    def get_stats(self) -> dict:
        """
        Return rate limiter statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_requests": self.request_count,
            "total_wait_time": self.total_wait_time,
            "avg_wait_per_request": (
                self.total_wait_time / self.request_count
                if self.request_count > 0
                else 0.0
            ),
            "is_off_peak": self.is_off_peak_hours(),
            "current_rate_limit": (
                self.requests_per_second_off_peak
                if self.is_off_peak_hours()
                else self.requests_per_second
            ),
        }

    def reset(self):
        """Reset the rate limiter statistics."""
        self.last_request_time = None
        self.request_count = 0
        self.total_wait_time = 0.0


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts the rate based on HTTP 429 errors.

    If we receive 429 (Too Many Requests), it automatically reduces the rate.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_429_count = 0
        self.rate_reduction_factor = 0.8  # Reduce to 80% after a 429 error

    def handle_429_error(self):
        """
        Adjust the rate limit after receiving a 429 error.

        Reduces the rate to 80% of the current value and increases delays.
        """
        self.error_429_count += 1

        # Reduce rate
        self.requests_per_second *= self.rate_reduction_factor
        self.requests_per_second_off_peak *= self.rate_reduction_factor

        # Increase delays
        self.min_delay /= self.rate_reduction_factor
        self.min_delay_off_peak /= self.rate_reduction_factor

        # Wait longer before the next request
        time.sleep(self.min_delay * 3)

    def get_stats(self) -> dict:
        """Return statistics including 429 errors."""
        stats = super().get_stats()
        stats["error_429_count"] = self.error_429_count
        return stats
