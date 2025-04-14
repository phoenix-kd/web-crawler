# Simple Web Crawler for Product URLs

This project contains a Python script that crawls website sitemaps to find and extract product URLs based on keywords and specific URL patterns.

## Features
-   Crawls websites starting from their `robots.txt` to find sitemap URLs.
-   Recursively processes sitemap indexes (sitemaps linking to other sitemaps).
-   Identifies product URLs based on:
    -   Configurable keywords 
    -   Configurable special regex patterns 
-   Allows setting URL limits per site to prevent excessive crawling.
-   Saves the found product URLs to a separate CSV file for each site in the `product_urls` directory.

## Setup

1.  **Clone the repository (or ensure you have the files):**
    ```bash
    # If you haven't already
    git clone git@github.com:phoenix-kd/web-crawler.git
    cd web-crawler
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Modify the `crawler_drive.py` script to configure the crawler:

-   **`sites`**: A list of tuples. Each tuple contains:
    -   The base URL of the website to crawl (e.g., `'https://www.example.com'`).
    -   An optional integer limit for the maximum number of product URLs to extract from that site (e.g., `100`). Use `None` for no limit.
-   **`product_keywords`**: A list of strings used to identify potential product URLs (case-insensitive match).
-   **`special_patterns`**: A dictionary where keys are descriptive names and values are raw regex strings used to identify product URLs.

## Running the Crawler

Execute the main script from the command line:

```bash
python crawler_drive.py
```

The script will:

1.  Print the configured sites, keywords, and patterns.
2.  Create the `product_urls` directory if it doesn't exist (relative to the script).
3.  Crawl sitemaps 
4.  Identify product URLs based on the configured keywords and patterns.
5.  Respect the URL limits set for each site.
6.  Save the results to `product_urls/<site_name>_product_urls.csv`.
7.  Print progress updates to the console.