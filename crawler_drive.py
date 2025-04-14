import asyncio
import os
from sitemap_searcher import SitemapSearcher
import os # Ensure os is imported

async def main():
    sites = [
        ('https://www.tatacliq.com', 100),
        ('https://www.virgio.com', None),
        ('https://www.westside.com', 75),
        ('https://www.nykaafashion.com', 75)
    ]
    
    base_urls = [url for url, _ in sites]
    url_limits = {url: limit for url, limit in sites if limit is not None}
    
    product_keywords = ["prod", "product", "products", "prods"]
    special_patterns = {
        "p": r"[/-]p[/-]|[/-]p$"
    }
    print(f"Looking for URLs containing keywords: {product_keywords}")
    print(f"Looking for special patterns: {list(special_patterns.keys())}\n")
    print("Processing the following sites:")
    for url, limit in sites:
        limit_text = f"{limit} URLs" if limit is not None else "all URLs"
        print(f"- {url}: {limit_text}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "product_urls")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    searcher = SitemapSearcher(base_urls, product_keywords, special_patterns, url_limits, output_dir)
    await searcher.search_sitemaps()

if __name__ == '__main__':
    asyncio.run(main())