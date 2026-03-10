import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path

# Optional: render JS-powered pages (React, Vue, etc.) with Playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False


def _fetch_html(url: str, headers: dict, use_js: bool = False):
    """
    Fetch page HTML. If use_js is True and Playwright is available, render the page
    to capture client-side content (React/SPA). Falls back to requests otherwise.
    Returns None on fetch/render failure so caller can skip the page.
    """
    if use_js and _HAS_PLAYWRIGHT:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(extra_http_headers=headers)
                try:
                    # Use load instead of networkidle - more reliable for React sites
                    page.goto(url, wait_until="load", timeout=30000)
                    # Wait for common React/SPA indicators to finish rendering
                    page.wait_for_timeout(2000)
                    html = page.content()
                    browser.close()
                    print(f"✅ Successfully rendered {url} with JavaScript")
                    return html
                except PlaywrightTimeoutError:
                    # Still get the content even if it times out
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
            # Fall back to plain requests
            try:
                resp = requests.get(url, headers=headers)
                resp.raise_for_status()
                return resp.text
            except Exception:
                return None
    # Fallback to plain requests
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def extract_information(urls_to_visit, headers, data, crawl_document_path, use_js: bool = True):
    while urls_to_visit:
        webpage = urls_to_visit.pop()
        html = _fetch_html(webpage, headers=headers, use_js=use_js)
        if not html:
            print(f"❌ Skipping {webpage} (fetch/render failed)")
            continue
        soup = BeautifulSoup(html, "html.parser")

        # Remove only truly unnecessary tags (scripts and styles)
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Extract all text content from the entire page
        full_text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace while preserving structure
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        cleaned_text = "\n".join(lines)

        data.append(f"URL: {webpage}")
        data.append(cleaned_text)

    print("✅ Semantic chunking complete")

    with open(crawl_document_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(data))

    print(f"📄 File saved successfully as {crawl_document_path}")
    return data


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
        
        #get the page to visit from the list
        current_url = urls_to_visit.pop()


        #skip if already visited
        if current_url in visited_url:
            continue
        visited_url.add(current_url)

        # request the target url (skip errors instead of aborting)
        html = _fetch_html(current_url, headers=headers, use_js=use_js)
        if not html:
            print(f"❌ Skipping {current_url} due to error: fetch/render failed")
            continue
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            print(f"❌ Skipping {current_url} due to parse error: {e}")
            continue

        #collect all the links 
        link_elements = soup.select('a[href]')
        for link_element in link_elements:
            url = link_element.get('href')

            #convert links to absolute links
            if not url.startswith('http'):
                absolute_url = requests.compat.urljoin(target_url , url)
            else:
                absolute_url = url

            #ensure the crawled link belongs to the target domain and hasn't 
            if (absolute_url.startswith(target_url) and absolute_url not in urls_to_visit):
                urls_to_visit.append(absolute_url)

        #update the crawl count
        crawl_count += 1
    
    urls_to_visit.reverse()
    print("Urls to visit" , urls_to_visit)
    # Save file
    # current_directory = os.path.dirname(os.path.abspath(__file__))
    # folder_path = os.path.join(current_directory , "Crawl Document")
    # if not os.path.exists(folder_path):
    #     os.makedirs(folder_path)

    # # safe_filename = main_url.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_")
    # crawl_document_path = os.path.join(folder_path, f"{user_email}.txt")

    # Pass through use_js so the caller controls whether to render JS
    return extract_information(urls_to_visit, headers, data, crawl_document_path, use_js=use_js)  # ✅ Return data to FastAPI

##################################################################

# parent_directory = Path(__file__).parent

# print("parent_directory --->" , parent_directory)
# folder_path = os.path.join(parent_directory, "Crawl Document")
# if not os.path.exists(folder_path):
#     os.makedirs(folder_path)


# crawling_document_name = os.path.join(folder_path , "whatsapp_ai_receptionist.txt")

# # if not os.path.exists(crawling_document_name):
# #     os.makedirs(crawling_document_name)


# crawler("https://www.gunadhyasoft.com/" , crawling_document_name)
##################################################################