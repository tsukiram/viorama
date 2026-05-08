# app/gemini_client/throttler.py

import time
import threading

class GeminiThrottler:
    """
    Throttles API requests to stay within Rate Limits.
    Standard Free Tier for many Gemini models is 15 RPM, 
    but some (like experimental or specific projects) might be 5 RPM.
    """
    _lock = threading.Lock()
    _request_timestamps = []
    
    # Configuration
    MAX_RPM = 5  # Based on the user's specific quota log
    WINDOW_SECONDS = 60

    @classmethod
    def wait_if_needed(cls):
        """
        Check if we need to wait before sending another request to avoid 429 error.
        Original logic disabled to remove 5 RPM limit.
        """
        pass
        # with cls._lock:
        #     now = time.time()
        #     
        #     # 1. Remove timestamps older than our window
        #     cls._request_timestamps = [ts for ts in cls._request_timestamps if now - ts < cls.WINDOW_SECONDS]
        #     
        #     # 2. Check if we've reached the limit
        #     if len(cls._request_timestamps) >= cls.MAX_RPM:
        #         # Find the oldest timestamp in the current window
        #         oldest_ts = min(cls._request_timestamps)
        #         # Calculate how long to sleep (61 seconds after the oldest to be safe)
        #         sleep_duration = (cls.WINDOW_SECONDS + 1) - (now - oldest_ts)
        #         
        #         if sleep_duration > 0:
        #             print(f"\n[Throttler] Rate limit protection: Reached {cls.MAX_RPM} RPM. Sleeping for {sleep_duration:.2f}s...")
        #             time.sleep(sleep_duration)
        #             # Update 'now' after sleeping to record correct timestamp
        #             now = time.time()
        #     
        #     # 3. Add the current (or post-sleep) timestamp
        #     cls._request_timestamps.append(now)

# Singleton-like usage: GeminiThrottler.wait_if_needed()
