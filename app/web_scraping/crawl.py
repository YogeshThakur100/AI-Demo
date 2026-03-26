import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False


def _fetch_html(url: str, headers: dict, use_js: bool = False):
    if use_js and _HAS_PLAYWRIGHT:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(extra_http_headers=headers)
                try:
                    page.goto(url, wait_until="load", timeout=30000)
                    page.wait_for_timeout(2000)
                    html = page.content()
                    browser.close()
                    print(f"✅ Successfully rendered {url} with JavaScript")
                    return html
                except PlaywrightTimeoutError:
                    try:
                        html = page.content()
                        browser.close()
                        print(f"⚠️ Page load timed out but returning partial content from {url}")
                        return html
                    except Exception:
                        browser.close()
                        return None
                except Exception as e:
                    browser.close()
                    print(f"⚠️ Playwright error for {url}: {str(e)}")
                    return None
        except Exception as e:
            print(f"⚠️ Playwright initialization failed: {str(e)}")
            try:
                resp = requests.get(url, headers=headers)
                resp.raise_for_status()
                return resp.text
            except Exception:
                return None
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def extract_information(urls_to_visit, headers, data, crawl_document_path, use_js: bool = True):
    count = 0
    urls_crawled = set()
    while urls_to_visit and count <= 20:
        webpage = urls_to_visit.pop()
        html = _fetch_html(webpage, headers=headers, use_js=use_js)
        print(f"total count of pages crawled {count} and currently crawling {webpage}")
        urls_crawled.add(webpage)
        count += 1
        if not html:
            print(f"❌ Skipping {webpage} (fetch/render failed)")
            continue
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        full_text = soup.get_text(separator="\n", strip=True)

        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        cleaned_text = "\n".join(lines)

        data.append(f"URL: {webpage}")
        data.append(cleaned_text)

    print("✅ Semantic chunking complete")

    with open(crawl_document_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(data))

    print(f"📄 File saved successfully as {crawl_document_path}")
    return urls_crawled


def crawler(target_url, crawl_document_path=None, user_email=None, use_js: bool = True):
    main_url = target_url
    crawl_count = 0
    headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/118.0.0.0 Safari/537.36"
            )
        }


    urls_to_visit = [target_url]
    visited_url = set()
    max_crawl = 1
    data = []
    while urls_to_visit and crawl_count < max_crawl:
        
        current_url = urls_to_visit.pop()

        if current_url in visited_url:
            continue
        visited_url.add(current_url)

        html = _fetch_html(current_url, headers=headers, use_js=use_js)
        if not html:
            print(f"❌ Skipping {current_url} due to error: fetch/render failed")
            continue
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            print(f"❌ Skipping {current_url} due to parse error: {e}")
            continue

        link_elements = soup.select('a[href]')
        for link_element in link_elements:
            url = link_element.get('href')

            if not url.startswith('http'):
                absolute_url = requests.compat.urljoin(target_url , url)
            else:
                absolute_url = url

            if (absolute_url.startswith(target_url) and absolute_url not in urls_to_visit):
                urls_to_visit.append(absolute_url)

        crawl_count += 1
    
    urls_to_visit.reverse()
    print("Urls to visit" , urls_to_visit)
    return extract_information(urls_to_visit, headers, data, crawl_document_path, use_js=use_js)