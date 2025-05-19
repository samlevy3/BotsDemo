import asyncio
import argparse
import os
import logging
from playwright.async_api import async_playwright, Playwright
from collections import deque
import time
from typing import Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Proxy configuration
PROXY_USER = os.getenv('PROXY_USER')
PROXY_PASS = os.getenv('PROXY_PASS')
PROXIES = os.getenv('PROXIES', '').split(',') if os.getenv('PROXIES') else []

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

    async def wait(self):
        now = time.time()
        
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        if len(self.requests) >= self.rate_limit:
            sleep_time = self.requests[0] - (now - self.time_window)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.requests.append(now)

async def run(playwright: Playwright, url: str, rate_limiter: RateLimiter, 
              use_proxy: bool = False, proxy: Optional[str] = None):
    """
    Function to run the browser impersonation test.
    It launches a browser instance, navigates to the specified URL,
    and checks if the page loads successfully.
    If a proxy is provided, it uses the proxy settings.
    It also implements a rate limiter to control the number of requests
    per second.

    :param playwright: The Playwright instance.
    :param url: The URL to navigate to.
    :param rate_limiter: The rate limiter instance.
    :param use_proxy: Whether to use a proxy or not.
    :param proxy: The proxy server address.
    :return: A tuple containing the success status and an error message if any.
    """
    try:
        await rate_limiter.wait()
        
        chromium = playwright.chromium
        browser = await chromium.launch(
            proxy={"server": proxy, "username": PROXY_USER, "password": PROXY_PASS}
            if use_proxy and proxy else None
        )
        context = await browser.new_context(
            ignore_https_errors=True,
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720},
            locale="en-US"
        )
        page = await context.new_page()

        response = await page.goto(url)
        if not response or response.status != 200:
            raise Exception(f"Non-200 status code: {response.status if response else 'No response'}")

        await page.wait_for_function(
            "document.body.innerText.includes('Destination')", 
            timeout=7000
        )

        await browser.close()
        return True, None

    except Exception as e:
        proxy_info = f"via {proxy}" if proxy else "direct connection"
        error_msg = f"Error during request ({proxy_info}): {e}"
        return False, error_msg

async def main(url: str, total_requests: int, concurrency: int, rate_limit: int, use_proxy: bool):
    """
    Main function to run the browser impersonation test.
    It initializes the Playwright instance, sets up the rate limiter,
    and runs multiple concurrent requests to the specified URL.
    It logs the results and provides summary statistics.
    
    :param url: The target URL to test.
    :param total_requests: Total number of requests to make.
    :param concurrency: Number of concurrent requests.
    :param rate_limit: Rate limit for requests per second.
    :param use_proxy: Whether to use a proxy or not.
    :return: None
    """
    success_count = 0
    failure_count = 0
    rate_limiter = RateLimiter(rate_limit)
    times = []
    
    logger.info("Starting browser impersonation test:")
    logger.info(f"Target URL: {url}")
    logger.info(f"Total requests: {total_requests}")
    logger.info(f"Concurrency: {concurrency}")
    logger.info(f"Rate limit: {rate_limit} req/sec")
    logger.info(f"Proxy enabled: {use_proxy}")

    async with async_playwright() as playwright:
        semaphore = asyncio.Semaphore(concurrency)
        
        async def worker(i: int):
            start_time = time.time()
            async with semaphore:
                proxy = PROXIES[i % len(PROXIES)] if use_proxy and PROXIES else None
                success, error = await run(playwright, url, rate_limiter, use_proxy, proxy)
                elapsed = time.time() - start_time
                times.append(elapsed)
                
                if success:
                    nonlocal success_count
                    success_count += 1
                    logger.info(f"Request {i} completed in {elapsed:.2f}s")
                else:
                    nonlocal failure_count
                    failure_count += 1
                    logger.error(f"Request {i} failed in {elapsed:.2f}s: {error}")

        tasks = [worker(i) for i in range(total_requests)]
        await asyncio.gather(*tasks)

    # Summary stats
    logger.info("\n--- Results ---")
    logger.info(f"Total successful calls: {success_count}")
    logger.info(f"Total failed calls: {failure_count}")
    logger.info(f"Success rate: {(success_count/total_requests)*100:.1f}%")
    
    if times:
        logger.info("\n--- Timing Stats ---")
        logger.info(f"Min time: {min(times):.3f}s")
        logger.info(f"Max time: {max(times):.3f}s")
        logger.info(f"Avg time: {sum(times)/len(times):.3f}s")

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
    parser.add_argument("-p", "--proxy", action="store_true",
                       help="Use proxy if available")
    args = parser.parse_args()

    asyncio.run(main(args.url, args.n, args.c, args.rate, args.proxy))