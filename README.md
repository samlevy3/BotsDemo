# Bot Demo Project

This project demonstrates different approaches to making HTTP requests to a target URL, including a basic bot and a browser impersonator bot. Both implementations support rate limiting and concurrent requests.

## Features

- Basic HTTP request bot
- Browser impersonation bot using Playwright
- Configurable rate limiting
- Concurrent request handling
- Optional proxy support (browser bot)
- Performance metrics
- Logging support

## Prerequisites

```bash
# Install required packages
pip install requests playwright python-dotenv

# Install Playwright browsers
playwright install
```

## Project Structure

```
bots_demo/
├── basic_bot/
│   └── basic_bot.py      # Simple requests-based bot
├── browser_impersonator/
│   └── browser_impersonator_bot.py  # Playwright-based bot
└── README.md
```

## Usage

### Basic Bot

Simple request-based bot using the `requests` library:

```bash
python basic_bot/basic_bot.py -n 60 -c 5 -r 5
```

Parameters:
- `-n`: Number of requests (default: 60)
- `-c`: Concurrency level (default: 5)
- `-r`: Rate limit in requests per second (default: 5)

### Browser Impersonator Bot

Advanced bot using Playwright for browser automation:

```bash
python browser_impersonator/browser_impersonator_bot.py -n 60 -c 5 -r 5 -p
```

Parameters:
- `-n`: Number of requests (default: 60)
- `-c`: Concurrency level (default: 5)
- `-r`: Rate limit in requests per second (default: 5)
- `-p`: Use proxy if available (optional)

### Proxy Configuration

To use proxies with the browser impersonator bot, create a `.env` file:

```plaintext
PROXY_USER=your_username
PROXY_PASS=your_password
PROXIES=http://proxy1.com:8080,http://proxy2.com:8080
```

## Features Comparison

| Feature              | Basic Bot | Browser Bot |
|---------------------|-----------|-------------|
| Rate Limiting       | ✅        | ✅          |
| Concurrency        | ✅        | ✅          |
| Proxy Support      | ❌        | ✅          |
| Browser Simulation | ❌        | ✅          |

## Output Metrics

Both bots provide detailed performance metrics including:
- Success/failure counts
- Request timing statistics

## Notes

- The browser impersonator bot provides better detection avoidance but uses more resources
- The basic bot is faster but more easily detected as automated traffic
- Rate limiting helps avoid overwhelming the target server
- Use proxy support carefully and in accordance with target site's terms of service