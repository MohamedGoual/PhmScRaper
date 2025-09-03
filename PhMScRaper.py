#!/usr/bin/env python3
import asyncio
import aiohttp
import aiofiles
import re
import json
import csv
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlencode
from collections import deque, defaultdict
import argparse
import sys
from pathlib import Path
import uvloop
from selectolax.parser import HTMLParser
import aiodns
from aiohttp_socks import ProxyType, ProxyConnector
import random
from functools import partial
import signal
import time
import os
import shutil
from dataclasses import dataclass, field
from typing import Set, List, Dict, Tuple, Optional
import warnings
from termcolor import colored
from pyfiglet import Figlet

warnings.filterwarnings('ignore')

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    class DummyColor:
        def __getattr__(self, name): return ""
    Fore = Back = Style = DummyColor()

def get_terminal_width():
    try:
        return min(shutil.get_terminal_size().columns, 70)
    except:
        return 40

def ClearScreen():
    os.system('cls' if os.name == 'nt' else 'clear')

def PrintColoredFigletWord():
    terminal_width = get_terminal_width()
    
    if terminal_width < 50:
        title = "PhMScRaper"
        print(colored("=" * min(len(title), terminal_width), "yellow", attrs=['bold']))
        print(colored(title.center(terminal_width), "green", attrs=['bold']))
        print(colored("=" * min(len(title), terminal_width), "red", attrs=['bold']))
    else:
        try:
            fig = Figlet(font='small')
            text = "PhMScRaper"
            rendered = fig.renderText(text)
            
            lines = rendered.splitlines()
            for line in lines:
                if len(line) > terminal_width:
                    line = line[:terminal_width-3] + "..."
                
                third = len(line) // 3
                colored_line = (
                    colored(line[:third], "yellow", attrs=['bold']) +
                    colored(line[third:2*third], "green", attrs=['bold']) +
                    colored(line[2*third:], "red", attrs=['bold'])
                )
                print(colored_line)
        except:
            title = "PhMScRaper"
            print(colored(title.center(terminal_width), "green", attrs=['bold']))

def PrintCharacterByCharacter(text, color, attrs=None, delay=0.005):
    terminal_width = get_terminal_width()
    
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line + " " + word) <= terminal_width - 2:
            current_line += " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    for line in lines:
        for char in line:
            print(colored(char, color, attrs=attrs), end='', flush=True)
            time.sleep(delay)
        print()

def PrintToolInfo():
    terminal_width = get_terminal_width()
    border = "─" * terminal_width
    print(colored(border, "red", attrs=["bold"]))

def RunIntro():
    Messages = [
        "This tool was developed by MohamedElGoual to help you extract phone numbers and email addresses from websites easily and quickly."
    ]
    ClearScreen()
    PrintColoredFigletWord()
    PrintToolInfo()
    for Message in Messages:
        terminal_width = get_terminal_width()
        border = "─" * terminal_width
        PrintCharacterByCharacter(Message, "red", attrs=["bold"])
        print(colored(border, "red", attrs=["bold"]))
        time.sleep(0.2)
    time.sleep(1)

@dataclass
class ScrapingResult:
    url: str
    emails: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    internal_links: Set[str] = field(default_factory=set)
    status_code: int = 0
    processing_time: float = 0.0
    error: str = ""

class UltraFastScraper:
    def __init__(self, max_concurrent=50, timeout=15, max_depth=3, delay=0.1):
        self.max_concurrent = max_concurrent
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_depth = max_depth
        self.delay = delay
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        
        self.email_patterns = [
            re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', re.IGNORECASE),
            re.compile(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', re.IGNORECASE),
            re.compile(r'[a-zA-Z0-9._%+-]+\s*(?:\[at\]|\(at\))\s*[a-zA-Z0-9.-]+\s*(?:\[dot\]|\(dot\))\s*[a-zA-Z]{2,}', re.IGNORECASE),
            re.compile(r'[a-zA-Z0-9._%+-]+&#64;[a-zA-Z0-9.-]+&#46;[a-zA-Z]{2,}', re.IGNORECASE)
        ]
        
        self.phone_patterns = [
            re.compile(r'\+\d{1,4}[\s\-\.]?\(?\d{1,4}\)?[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,9}', re.IGNORECASE),
            re.compile(r'\b\d{3}[\s\-\.]?\d{3}[\s\-\.]?\d{4}\b', re.IGNORECASE),
            re.compile(r'\b\d{4}[\s\-\.]?\d{3}[\s\-\.]?\d{4}\b', re.IGNORECASE),
            re.compile(r'(?:tel|phone|mobile|cell)[\s:]*([+\d\s\-\(\)\.]{7,})', re.IGNORECASE),
            re.compile(r'href=["\']tel:([+\d\s\-\(\)\.]+)["\']', re.IGNORECASE),
            re.compile(r'\b(?:00|\+)\d{10,15}\b', re.IGNORECASE),
            re.compile(r'\b0\d{9,10}\b', re.IGNORECASE)
        ]
        
        self.blocked_extensions = {
            '.css', '.js', '.json', '.xml', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.ppt', '.pptx', '.zip', '.rar', '.tar', '.gz', '.7z', '.exe', '.dmg',
            '.pkg', '.deb', '.rpm', '.msi', '.apk', '.ipa', '.mp3', '.mp4', '.avi',
            '.mov', '.wmv', '.flv', '.webm', '.mkv', '.jpg', '.jpeg', '.png', '.gif',
            '.bmp', '.svg', '.ico', '.webp', '.tiff', '.eps', '.ai', '.psd', '.sketch',
            '.woff', '.woff2', '.ttf', '.otf', '.eot'
        }
        
        self.blocked_patterns = [
            re.compile(r'/wp-content/(?:themes|plugins|uploads)/', re.IGNORECASE),
            re.compile(r'/assets?/', re.IGNORECASE),
            re.compile(r'/static/', re.IGNORECASE),
            re.compile(r'/media/', re.IGNORECASE),
            re.compile(r'/files?/', re.IGNORECASE),
            re.compile(r'/downloads?/', re.IGNORECASE),
            re.compile(r'/images?/', re.IGNORECASE),
            re.compile(r'\.(?:css|js|json|xml)(?:\?|$)', re.IGNORECASE)
        ]
        
        self.processed_urls = set()
        self.results = []
        self.session = None
        self.semaphore = None

    async def __aenter__(self):
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent * 2,
            limit_per_host=20,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers={'Accept-Encoding': 'gzip, deflate'},
            trust_env=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def get_random_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

    def normalize_url(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url.rstrip('/')

    def should_skip_url(self, url):
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        
        for ext in self.blocked_extensions:
            if path_lower.endswith(ext):
                return True
        
        for pattern in self.blocked_patterns:
            if pattern.search(url):
                return True
        
        if any(keyword in path_lower for keyword in ['admin', 'login', 'register', 'logout', 'cart', 'checkout']):
            return True
            
        return False

    def extract_emails(self, text):
        emails = set()
        for pattern in self.email_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[-1]
                
                email = str(match).strip().lower()
                email = re.sub(r'\s*\[at\]\s*', '@', email)
                email = re.sub(r'\s*\(at\)\s*', '@', email)
                email = re.sub(r'\s*\[dot\]\s*', '.', email)
                email = re.sub(r'\s*\(dot\)\s*', '.', email)
                email = re.sub(r'&#64;', '@', email)
                email = re.sub(r'&#46;', '.', email)
                email = email.replace('mailto:', '')
                
                if self.is_valid_email(email):
                    emails.add(email)
        
        return emails

    def extract_phones(self, text):
        phones = set()
        for pattern in self.phone_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[-1]
                
                phone = str(match).strip()
                phone = re.sub(r'[^\d+\-\(\)\s\.]', '', phone)
                phone = re.sub(r'\s+', ' ', phone).strip()
                
                if self.is_valid_phone(phone):
                    phones.add(phone)
        
        return phones

    def is_valid_email(self, email):
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            return False
        
        if len(email) > 254 or len(email) < 5:
            return False
        
        if re.search(r'\.{2,}|@{2,}|\.@|@\.|^[\.@]|[\.@]$', email):
            return False
        
        invalid_patterns = [
            'test@test', 'example@example', 'admin@admin', 'ajax-loader@2x.gif',
            'image@2x.', 'icon@2x.', 'logo@2x.', 'sprite@2x.', 'button@2x.',
            '@2x.gif', '@2x.png', '@2x.jpg', '@2x.jpeg', '@3x.', '@4x.'
        ]
        
        email_lower = email.lower()
        if any(invalid in email_lower for invalid in invalid_patterns):
            return False
        
        if re.search(r'@\d+x\.(gif|png|jpg|jpeg|svg|webp|ico)', email_lower):
            return False
        
        if email_lower.count('.') > 3:
            return False
        
        try:
            local, domain = email.rsplit('@', 1)
            if len(local) > 64 or len(domain) > 253:
                return False
            if not re.match(r'^[a-zA-Z0-9._%+-]+$', local):
                return False
            if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
                return False
            
            if any(ext in domain.lower() for ext in ['.gif', '.png', '.jpg', '.jpeg', '.svg', '.webp', '.ico', '.css', '.js']):
                return False
            
            return True
        except:
            return False

    def is_valid_phone(self, phone):
        if not phone:
            return False
        
        digits_only = re.sub(r'[^\d]', '', phone)
        
        if len(digits_only) < 7 or len(digits_only) > 15:
            return False
        
        if len(set(digits_only)) <= 2:
            return False
        
        if digits_only.startswith('0000') or digits_only.startswith('1111'):
            return False
        
        invalid_numbers = [
            '123456789', '987654321', '000000000', '111111111',
            '1543499459', '1548695607', '1743524863', '1752638227', '1752773913'
        ]
        if any(pattern in digits_only for pattern in invalid_numbers):
            return False
        
        invalid_ranges = [
            ('0102', '0103'), ('0128', '0129'), ('0152', '0153'),
            ('0168', '0169'), ('0300', '0301'), ('0303', '0304'),
            ('0308', '0309'), ('0400', '0450'), ('0460', '0520'),
            ('0490', '0491'), ('2000', '2060')
        ]
        
        for start_range, end_range in invalid_ranges:
            if digits_only.startswith(start_range) or digits_only.startswith(end_range):
                return False
            
            if len(digits_only) >= 4:
                phone_prefix = digits_only[:4]
                try:
                    if int(start_range) <= int(phone_prefix) <= int(end_range):
                        return False
                except ValueError:
                    continue
        
        return True

    def extract_links(self, html_content, base_url):
        try:
            tree = HTMLParser(html_content)
            links = set()
            
            for a_tag in tree.css('a[href]'):
                href = a_tag.attributes.get('href', '').strip()
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                
                try:
                    absolute_url = urljoin(base_url, href)
                    parsed_base = urlparse(base_url)
                    parsed_link = urlparse(absolute_url)
                    
                    if parsed_link.netloc == parsed_base.netloc and not self.should_skip_url(absolute_url):
                        links.add(absolute_url.split('#')[0])
                except:
                    continue
            
            return links
        except:
            return set()

    async def fetch_url(self, url):
        if url in self.processed_urls:
            return None
        
        self.processed_urls.add(url)
        start_time = time.time()
        
        async with self.semaphore:
            try:
                headers = self.get_random_headers()
                async with self.session.get(url, headers=headers, allow_redirects=True, ssl=False) as response:
                    
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type:
                        return None
                    
                    content = await response.text(errors='ignore')
                    processing_time = time.time() - start_time
                    
                    emails = self.extract_emails(content)
                    phones = self.extract_phones(content)
                    internal_links = self.extract_links(content, url)
                    
                    result = ScrapingResult(
                        url=url,
                        emails=emails,
                        phones=phones,
                        internal_links=internal_links,
                        status_code=response.status,
                        processing_time=processing_time
                    )
                    
                    url_display = url
                    terminal_width = get_terminal_width()
                    if len(url_display) > terminal_width - 20:
                        url_display = url_display[:terminal_width-23] + "..."
                    print(f"{colored(url_display, 'green', attrs=['bold'])}")
                    return result
                    
            except asyncio.TimeoutError:
                url_display = url[:50] + "..." if len(url) > 50 else url
                print(f"{colored(url_display, 'yellow', attrs=['bold'])}")
                return ScrapingResult(url=url, error="Timeout", processing_time=time.time() - start_time)
            except Exception as e:
                url_display = url[:50] + "..." if len(url) > 50 else url
                print(f"{colored(url_display, 'red', attrs=['bold'])} - {colored(str(e)[:23], 'yellow', attrs=['bold'])}")
                return ScrapingResult(url=url, error=str(e), processing_time=time.time() - start_time)
            finally:
                if self.delay > 0:
                    await asyncio.sleep(self.delay)

    async def scrape_website(self, start_url):
        start_url = self.normalize_url(start_url)
        
        urls_to_process = deque([(start_url, 0)])
        all_results = []
        
        while urls_to_process:
            batch = []
            for _ in range(min(self.max_concurrent, len(urls_to_process))):
                if urls_to_process:
                    batch.append(urls_to_process.popleft())
            
            tasks = []
            for url, depth in batch:
                if depth <= self.max_depth:
                    tasks.append(self.fetch_url(url))
            
            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, ScrapingResult) and result.internal_links:
                        all_results.append(result)
                        
                        if result.status_code == 200:
                            for link in list(result.internal_links)[:10]:
                                if link not in self.processed_urls:
                                    current_depth = next((d for u, d in batch if u == result.url), 0)
                                    urls_to_process.append((link, current_depth + 1))
                    elif isinstance(result, ScrapingResult):
                        all_results.append(result)
        
        return all_results

    async def scrape_multiple_websites(self, urls):
        print(colored("\nTool Starting Pleae wait...", "green", attrs=["bold"]))
        
        tasks = []
        for url in urls:
            tasks.append(self.scrape_website(url))
        
        all_results = []
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for task_results in completed_tasks:
            if isinstance(task_results, list):
                all_results.extend(task_results)
        
        self.results = all_results
        return all_results

    def export_results(self, results, output_format="all", output_dir=None):
        if not results:
            print(colored("❌ No results to export", "red", attrs=["bold"]))
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_dir is None:
            output_dir = f"scraped_data_{timestamp}"
        
        Path(output_dir).mkdir(exist_ok=True)
        
        all_emails = set()
        all_phones = set()
        url_stats = defaultdict(lambda: {'emails': set(), 'phones': set()})
        
        for result in results:
            all_emails.update(result.emails)
            all_phones.update(result.phones)
            url_stats[result.url]['emails'].update(result.emails)
            url_stats[result.url]['phones'].update(result.phones)
        
        if output_format in ["txt", "all"] and (all_emails or all_phones):
            if all_emails:
                with open(f"{output_dir}/emails.txt", 'w', encoding='utf-8') as f:
                    for email in sorted(all_emails):
                        f.write(f"{email}\n")
            
            if all_phones:
                with open(f"{output_dir}/phones.txt", 'w', encoding='utf-8') as f:
                    for phone in sorted(all_phones):
                        f.write(f"{phone}\n")
        
        if output_format in ["csv", "all"]:
            with open(f"{output_dir}/detailed_results.csv", 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['URL', 'Type', 'Value', 'Status', 'Processing_Time'])
                
                for result in results:
                    for email in result.emails:
                        writer.writerow([result.url, 'Email', email, result.status_code, f"{result.processing_time:.2f}"])
                    for phone in result.phones:
                        writer.writerow([result.url, 'Phone', phone, result.status_code, f"{result.processing_time:.2f}"])
        
        if output_format in ["json", "all"]:
            export_data = {
                'scraping_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'total_websites_scraped': len({r.url for r in results}),
                    'successful_requests': len([r for r in results if r.status_code == 200]),
                    'total_emails_found': len(all_emails),
                    'total_phones_found': len(all_phones),
                    'settings': {
                        'max_concurrent': self.max_concurrent,
                        'timeout': self.timeout.total,
                        'max_depth': self.max_depth
                    }
                },
                'results': [
                    {
                        'url': result.url,
                        'emails': list(result.emails),
                        'phones': list(result.phones),
                        'status_code': result.status_code,
                        'processing_time': result.processing_time,
                        'links_found': len(result.internal_links),
                        'error': result.error
                    } for result in results
                ]
            }
            
            with open(f"{output_dir}/complete_results.json", 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        terminal_width = get_terminal_width()
        border = "═" * terminal_width
        
        print(f"\n{colored(border, 'green', attrs=['bold'])}")
        print(f"{colored('SCRAPING RESULTS SUMMARY', 'green', attrs=['bold']).center(terminal_width + 0)}")
        print(f"{colored(border, 'green', attrs=['bold'])}")
        print(f"{colored(f'Results exported to: {output_dir}', 'green', attrs=['bold'])}")
        print(f"{colored(f'Total emails found: {len(all_emails)}', 'green', attrs=['bold'])}")
        print(f"{colored(f'Total phones found: {len(all_phones)}', 'green', attrs=['bold'])}")
        print(f"{colored(f'Websites processed: {len({r.url for r in results})}', 'green', attrs=['bold'])}")
        print(f"{colored(border, 'green', attrs=['bold'])}")

def load_urls_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return urls
    except FileNotFoundError:
        print(colored(f"❌ File not found: {file_path}", "red", attrs=["bold"]))
        return []

async def main():
    parser = argparse.ArgumentParser(description="Ultra Fast Web Scraper")
    parser.add_argument("-u", "--urls", nargs="+", help="URLs to scrape")
    parser.add_argument("-f", "--file", help="File containing URLs")
    parser.add_argument("-c", "--concurrent", type=int, default=50, help="Max concurrent requests")
    parser.add_argument("-t", "--timeout", type=int, default=15, help="Request timeout")
    parser.add_argument("-d", "--depth", type=int, default=3, help="Max crawling depth")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests")
    parser.add_argument("--format", choices=["txt", "csv", "json", "all"], default="all", help="Export format")
    parser.add_argument("-o", "--output", help="Output directory")

    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        try:
            RunIntro()
            print("\n" + colored("Tool Starting...", "green", attrs=["bold"]))
        except KeyboardInterrupt:
            ClearScreen()
            print("\n" + colored("Goodbye!", "yellow", attrs=["bold"]))
            sys.exit(0)
        parser.print_help()
        return
    
    urls = []
    if args.file:
        urls.extend(load_urls_from_file(args.file))
    if args.urls:
        urls.extend(args.urls)
    
    if not urls:
        print(colored("❌ No URLs provided", "red", attrs=["bold"]))
        return
    
    start_time = time.time()
    
    async with UltraFastScraper(
        max_concurrent=args.concurrent,
        timeout=args.timeout,
        max_depth=args.depth,
        delay=args.delay
    ) as scraper:
        
        results = await scraper.scrape_multiple_websites(urls)
        scraper.export_results(results, args.format, args.output)
    
    total_time = time.time() - start_time
    print(colored(f"\nTotal execution time: {total_time:.2f} seconds", "cyan", attrs=["bold"]))

if __name__ == "__main__":
    try:
        RunIntro()
        print()
    except KeyboardInterrupt:
        ClearScreen()
        print("\n" + colored("Goodbye!", "yellow", attrs=["bold"]))
        sys.exit(0)
    try:
        if len(sys.argv) == 1:
            RunIntro()
            print("\n" + colored("Use --help to see available options", "yellow", attrs=["bold"]))
            sys.exit(0)
        asyncio.run(main())
    except KeyboardInterrupt:
        print(colored("\n🛑 Scraping interrupted by user", "yellow", attrs=["bold"]))
        sys.exit(0)
    except Exception as e:
        print(colored(f"\n💥 Fatal error: {e}", "red", attrs=["bold"]))
        sys.exit(1)