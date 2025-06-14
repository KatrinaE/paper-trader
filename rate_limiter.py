import logging

# Configure rate limiter logger
logger = logging.getLogger('rate_limiter')

class RateLimiter:
    def __init__(self, max_calls, window_seconds):
        """Initialize rate limiter with maximum calls and window duration.

        Args:
            max_calls: Maximum number of calls allowed in the window
            window_seconds: Duration of the window in seconds
        """
        logger.info(f"Initializing RateLimiter: max_calls={max_calls}, window_seconds={window_seconds}")
        logger.info(f"Initializing RateLimiter: max_calls={max_calls}, window_seconds={window_seconds}")
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []


    def wait_if_needed(self):
        """Wait if we've reached the rate limit.

        This method will:
        1. Remove old calls from the list
        2. Check if we've reached the limit
        3. Wait if needed
        4. Record the current call
        """
        # Remove old calls from the list
        now = time.time()
        self.calls = [call for call in self.calls if now - call <= self.window_seconds]

        # If we've reached the limit, wait until we can make another call
        if len(self.calls) >= self.max_calls:
            time_to_wait = self.calls[0] + self.window_seconds - now
            if time_to_wait > 0:
                logger.warning(f"Rate limit reached. Waiting {time_to_wait:.1f} seconds...")
                time.sleep(time_to_wait)

        # Record this call
        self.calls.append(time.time())
        logger.debug(f"Call recorded, current calls in window: {len(self.calls)}")
