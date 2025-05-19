import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def make_request(session, url):
    """
    Function to make a GET request to the specified URL.
    It returns the status code, elapsed time, and size of the response. 

    :param session: requests.Session object
    :param url: URL to send the request to
    :return: tuple (status_code, elapsed_time, size)
    """
    start = time.time()
    resp = session.get(url)
    logger.info(f"Response: {resp.content}")
    elapsed = time.time() - start
    return resp.status_code, elapsed

class RateLimiter:
    """
    A simple rate limiter to control the number of requests per second.
    It uses a deque to keep track of the timestamps of the requests.
    When a new request is made, it checks if the oldest request in the deque
    is older than the time window. If it is, it removes it from the deque.
    If the deque is full (i.e., the number of requests in the time window
    exceeds the rate limit), it calculates the sleep time until the next
    request can be made.

    :param rate_limit: Maximum number of requests per second
    :param time_window: Time window in seconds to consider for rate limiting
    """
    def __init__(self, rate_limit, time_window=1):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.requests = deque()

    def wait(self):
        now = time.time()
        
        # Remove old requests outside the time window
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        # If at rate limit, wait until oldest request expires
        if len(self.requests) >= self.rate_limit:
            sleep_time = self.requests[0] - (now - self.time_window)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self.requests.append(now)

def run_basic_bot(url, n, c, rate):
    rate_limiter = RateLimiter(rate_limit=rate)
    
    with requests.Session() as session:
        results = []
        logger.info(f"Sending {n} requests to {url} with concurrency {c}...")
        logger.info(f"Rate limited to {rate} requests per second")

        with ThreadPoolExecutor(max_workers=c) as executor:
            futures = []
            for _ in range(n):
                rate_limiter.wait()
                futures.append(executor.submit(make_request, session, url))
                
            for future in as_completed(futures):
                try:
                    status, elapsed = future.result()
                    results.append((status, elapsed))
                    logger.info(f"Request completed: status={status}, time={elapsed:.2f}s")
                except Exception as e:
                    logger.error(f"Request failed: {str(e)}")
                    results.append((0, 0, 0))

    # Summary
    success = [r for r in results if r[0] == 200]
    failed = [r for r in results if r[0] != 200]
    times = [r[1] for r in results if r[0] == 200]

    logger.info("\n--- Benchmark Summary ---")
    logger.info(f"Total requests: {n}")
    logger.info(f"Successful: {len(success)}")
    logger.info(f"Failed: {len(failed)}")
    
    if times:
        logger.info("\n--- Timing Stats ---")
        logger.info(f"Min time: {min(times):.3f}s")
        logger.info(f"Max time: {max(times):.3f}s")
        logger.info(f"Avg time: {sum(times)/len(times):.3f}s")
    else:
        logger.warning("No successful responses to measure time.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", required=True,
                       help="Target URL")
    parser.add_argument("-n", type=int, default=60,
                       help="Total number of requests")
    parser.add_argument("-c", type=int, default=5,
                       help="Concurrency level")
    parser.add_argument("-r", "--rate", type=int, default=5,
                       help="Rate limit (requests per second)")
    args = parser.parse_args()

    run_basic_bot(args.url, args.n, args.c, args.rate)
