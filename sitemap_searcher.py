import re
import csv
import gzip
import io
import requests
import os
import tempfile
from urllib.parse import urlparse, urljoin
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

class SitemapSearcher:
    def __init__(self, base_urls, product_keywords, special_patterns=None, url_limits=None, output_dir=None):
        self.base_urls = base_urls
        self.product_keywords = product_keywords
        self.special_patterns = special_patterns or {}
        self.browser_conf = BrowserConfig(headless=True)
        self.run_conf = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        self.temp_files = set()
        self.url_limits = url_limits or {}
        self.url_counts = {}
        self.output_dir = output_dir or "."

    def _is_product_url(self, url):
        if any(re.search(pattern, url) for pattern in self.special_patterns.values()):
            return True
        if any(keyword.lower() in url.lower() for keyword in self.product_keywords):
            return True
        return False

    async def search_sitemaps(self):
        async with AsyncWebCrawler(config=self.browser_conf) as crawler:
            for base_url in self.base_urls:
                self.url_counts[base_url] = 0
                site_name = urlparse(base_url).netloc.replace('www.', '')
                csv_filename = os.path.join(self.output_dir, f"{site_name}_product_urls.csv")
                
                with open(csv_filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['URL'])
                
                await self._process_site(crawler, base_url, csv_filename)

    def _cleanup_temp_files(self):
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    print(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                print(f"Error cleaning up temporary file {temp_file}: {e}")
        self.temp_files.clear()

    async def _process_site(self, crawler, base_url, csv_filename):
        robots_url = urljoin(base_url, '/robots.txt')
        print(f"Checking robots.txt for {base_url}...")
        
        try:
            robots_result = await crawler.arun(robots_url, config=self.run_conf)
            print("Robots.txt found successfully")
            robots_content = robots_result.markdown

            sitemap_urls = self._extract_sitemap_urls(robots_content)
            if not sitemap_urls:
                print(f"No Sitemaps found in robots.txt\n")
                return

            print(f"\nCrawling {len(sitemap_urls)} unique Sitemap(s) for {base_url}...")
            total_product_urls = await self._process_sitemaps(crawler, sitemap_urls, csv_filename, base_url)
            
            print(f"Total product URLs found for {urlparse(base_url).netloc}: {total_product_urls}")
            print(f"URLs have been saved to {csv_filename}\n")

        except Exception as e:
            print(f"Robots.txt not found or error accessing it: {e}\n")

    def _extract_sitemap_urls(self, robots_content):
        sitemap_urls = set()
        for line in robots_content.splitlines():
            match = re.match(r"^\s*Sitemap\s*:\s*(?P<url>\S+)", line, re.IGNORECASE)
            if match:
                sitemap_url = match.group('url').strip()
                sitemap_urls.add(sitemap_url)
                print(f"Found Sitemap: {sitemap_url}")
        return sitemap_urls

    async def _process_sitemaps(self, crawler, sitemap_urls, csv_filename, base_url):
        total_product_urls = 0
        url_limit = self.url_limits.get(base_url)
        
        for sitemap_url in sitemap_urls:
            if url_limit and self.url_counts[base_url] >= url_limit:
                print(f"\nReached URL limit of {url_limit} for {base_url}. Stopping further processing.")
                break
                
            print(f"Crawling Sitemap: {sitemap_url}")
            try:
                sitemap_result = await crawler.arun(sitemap_url, config=self.run_conf)
                print(f"--- Parsing Sitemap: {sitemap_url} ---")
                
                gz_urls = set()
                xml_urls = set()
                found_urls = []
                
                for line in sitemap_result.markdown.splitlines():
                    url_match = re.search(r'<loc>(.*?)</loc>', line)
                    if url_match:
                        url = url_match.group(1).strip()
                        if url.endswith('.gz'):
                            gz_urls.add(url)
                        elif '.xml' in url:
                            if self._is_product_url(url):
                                xml_urls.add(url)
                                print(f"Found product XML URL: {url}")
                        elif self._is_product_url(url):
                            if not url.endswith('.xml'):
                                found_urls.append(url)
                
                if found_urls:
                    if url_limit:
                        remaining = url_limit - self.url_counts[base_url]
                        if remaining <= 0:
                            break
                        found_urls = found_urls[:remaining]
                    
                    self._save_urls_to_csv(found_urls, csv_filename)
                    self.url_counts[base_url] += len(found_urls)
                    total_product_urls += len(found_urls)
                
                for xml_url in xml_urls:
                    if url_limit and self.url_counts[base_url] >= url_limit:
                        print(f"\nReached URL limit of {url_limit} for {base_url}. Stopping further processing.")
                        break
                        
                    print(f"\nProcessing product XML URL: {xml_url}")
                    xml_urls_found = await self._process_xml_url(crawler, xml_url, csv_filename, base_url)
                    total_product_urls += xml_urls_found
                
                for gz_url in gz_urls:
                    if url_limit and self.url_counts[base_url] >= url_limit:
                        print(f"\nReached URL limit of {url_limit} for {base_url}. Stopping further processing.")
                        break
                        
                    print(f"\nProcessing gzipped sitemap: {gz_url}")
                    gz_urls_found = await self._process_single_gz_file(gz_url, csv_filename, base_url)
                    total_product_urls += gz_urls_found
                    
                    self._cleanup_temp_files()
                
                print(f"Found {len(found_urls)} direct product URLs in this sitemap")
                print("--- End Sitemap Parsing ---\n")

            except Exception as e:
                print(f"  Error crawling Sitemap {sitemap_url}: {e}\n")
        
        return total_product_urls

    async def _process_xml_url(self, crawler, url, csv_filename, base_url):
        try:
            print(f"Fetching XML content from: {url}")
            
            xml_result = await crawler.arun(url, config=self.run_conf)
            xml_content = xml_result.markdown
            
            found_urls = []
            nested_xml_urls = set()
            
            for line in xml_content.splitlines():
                url_match = re.search(r'<loc>(.*?)</loc>', line)
                if url_match:
                    url = url_match.group(1).strip()
                    if self._is_product_url(url):
                        if url.endswith('.xml'):
                            nested_xml_urls.add(url)
                            print(f"Found nested product XML URL: {url}")
                        elif not url.endswith('.gz'):
                            found_urls.append(url)
            
            url_limit = self.url_limits.get(base_url)
            if url_limit:
                remaining = url_limit - self.url_counts[base_url]
                if remaining <= 0:
                    return 0
                found_urls = found_urls[:remaining]
            
            if found_urls:
                self._save_urls_to_csv(found_urls, csv_filename)
                self.url_counts[base_url] += len(found_urls)
                print(f"Found {len(found_urls)} product URLs in XML content")
            
            total_nested_urls = 0
            for nested_url in nested_xml_urls:
                if url_limit and self.url_counts[base_url] >= url_limit:
                    print(f"\nReached URL limit of {url_limit} for {base_url}. Stopping further processing.")
                    break
                    
                print(f"\nProcessing nested product XML URL: {nested_url}")
                nested_urls_found = await self._process_xml_url(crawler, nested_url, csv_filename, base_url)
                total_nested_urls += nested_urls_found
            
            return len(found_urls) + total_nested_urls
                    
        except Exception as e:
            print(f"Error processing XML URL {url}: {e}")
            return 0

    async def _process_single_gz_file(self, url, csv_filename, base_url):
        try:
            print(f"Downloading gzipped sitemap: {url}")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gz') as temp_file:
                temp_path = temp_file.name
                self.temp_files.add(temp_path)
                
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
            
            found_urls = []
            with gzip.open(temp_path, 'rb') as gz_file:
                decompressed_content = gz_file.read().decode('utf-8')
                
                for line in decompressed_content.splitlines():
                    url_match = re.search(r'<loc>(.*?)</loc>', line)
                    if url_match:
                        url = url_match.group(1).strip()
                        if self._is_product_url(url):
                            if not url.endswith('.xml') and not url.endswith('.gz'):
                                found_urls.append(url)
            
            url_limit = self.url_limits.get(base_url)
            if url_limit:
                remaining = url_limit - self.url_counts[base_url]
                if remaining <= 0:
                    return 0
                found_urls = found_urls[:remaining]
            
            if found_urls:
                self._save_urls_to_csv(found_urls, csv_filename)
                self.url_counts[base_url] += len(found_urls)
                print(f"Found {len(found_urls)} product URLs in gzipped sitemap")
            
            return len(found_urls)
                    
        except Exception as e:
            print(f"Error processing gzipped sitemap {url}: {e}")
            return 0

    def _save_urls_to_csv(self, urls, csv_filename):
        with open(csv_filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for url in urls:
                writer.writerow([url]) 