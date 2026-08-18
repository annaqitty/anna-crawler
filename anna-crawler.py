import os
import time
import json
import hashlib
import threading
from pathlib import Path
from urllib.parse import urlparse, urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from colorama import Fore, Style, init


# ============================================================
# WINDOWS / POWERSHELL COLOR SUPPORT
# ============================================================

init(autoreset=True)

GREEN = Fore.GREEN
RED = Fore.RED
YELLOW = Fore.YELLOW
CYAN = Fore.CYAN
MAGENTA = Fore.MAGENTA
WHITE = Fore.WHITE
BLUE = Fore.BLUE
RESET = Style.RESET_ALL


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path.cwd()
DOWNLOAD_DIR = BASE_DIR / "Downloaded-Files"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_TYPES = {
    "csv": ".csv",
    "txt": ".txt",
    "log": ".log",
    "pdf": ".pdf",
    "xlsx": ".xlsx",
}

MAX_SEARCH_PAGES = 1000
MAX_FILE_SIZE = 100 * 1024 * 1024
REQUEST_TIMEOUT = 30


# Optional SearXNG instance.
# Example: http://localhost:8080
SEARXNG_URL = os.getenv(
    "SEARXNG_URL",
    ""
).rstrip("/")


# Optional Bing-compatible API.
BING_ENDPOINT = os.getenv(
    "SEARCH_ENDPOINT",
    ""
).strip()

BING_API_KEY = os.getenv(
    "SEARCH_API_KEY",
    ""
).strip()


# Common Crawl index.
COMMON_CRAWL_INDEX = os.getenv(
    "COMMON_CRAWL_INDEX",
    "CC-MAIN-2025-30"
).strip()


# ============================================================
# LOGO
# ============================================================

def logo():
    print(
        f"""
{CYAN}╔══════════════════════════════════════════════════════════╗
║                                                          ║
║        MULTI-SOURCE PUBLIC FILE DISCOVERY TOOL           ║
║                                                          ║
║       SEARXNG + COMMON CRAWL + OPTIONAL API              ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝{RESET}
"""
    )


# ============================================================
# USER INPUT
# ============================================================

def get_keywords():
    while True:
        raw = input(
            f"{CYAN}[INPUT]{RESET} Keywords: "
        ).strip()

        keywords = [
            x.strip()
            for x in raw.split(",")
            if x.strip()
        ]

        if keywords:
            return keywords

        print(
            f"{RED}[ERROR]{RESET} "
            "Enter at least one keyword."
        )


def get_threads():
    while True:
        try:
            value = input(
                f"{CYAN}[INPUT]{RESET} "
                "Threads [10]: "
            ).strip()

            threads = int(value or "10")

            if threads < 1:
                raise ValueError

            return min(threads, 100)

        except ValueError:
            print(
                f"{RED}[ERROR]{RESET} "
                "Enter a valid number."
            )


def get_pages():
    while True:
        try:
            value = input(
                f"{CYAN}[INPUT]{RESET} "
                f"Maximum pages [1-{MAX_SEARCH_PAGES}]: "
            ).strip()

            pages = int(value or "10")

            if pages < 1:
                raise ValueError

            return min(
                pages,
                MAX_SEARCH_PAGES
            )

        except ValueError:
            print(
                f"{RED}[ERROR]{RESET} "
                "Enter a valid number."
            )


def get_file_types():
    print()
    print(
        f"{CYAN}Available:{RESET} "
        "csv, txt, log, pdf, xlsx"
    )

    raw = input(
        f"{CYAN}[INPUT]{RESET} "
        "File types [all]: "
    ).strip().lower()

    if not raw or raw == "all":
        return list(SUPPORTED_TYPES.keys())

    result = []

    for item in raw.split(","):
        item = item.strip().lstrip(".")

        if item in SUPPORTED_TYPES:
            result.append(item)

    result = list(dict.fromkeys(result))

    return result or list(SUPPORTED_TYPES.keys())


# ============================================================
# SEARXNG SEARCH
# ============================================================

def search_searxng(
    keyword,
    extension,
    max_pages
):
    urls = set()

    if not SEARXNG_URL:
        return urls

    query = (
        f'"{keyword}" '
        f"filetype:{extension}"
    )

    for page in range(1, max_pages + 1):
        try:
            params = {
                "q": query,
                "format": "json",
                "pageno": page,
            }

            response = requests.get(
                f"{SEARXNG_URL}/search",
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            data = response.json()

            results = data.get(
                "results",
                []
            )

            if not results:
                print(
                    f"{YELLOW}[SEARXNG END]{RESET} "
                    f"{keyword} | .{extension}"
                )
                break

            new_count = 0

            for item in results:
                url = item.get("url", "").strip()

                if url and urlparse(
                    url
                ).path.lower().endswith(
                    SUPPORTED_TYPES[extension]
                ):
                    if url not in urls:
                        urls.add(url)
                        new_count += 1

            print(
                f"{CYAN}[SEARXNG]{RESET} "
                f"{YELLOW}{keyword}{RESET} | "
                f"{MAGENTA}.{extension}{RESET} | "
                f"Page {GREEN}{page}{RESET} | "
                f"New {GREEN}{new_count}{RESET}"
            )

            time.sleep(0.2)

        except Exception as error:
            print(
                f"{RED}[SEARXNG ERROR]{RESET} "
                f"{error}"
            )
            break

    return urls


# ============================================================
# BING-COMPATIBLE SEARCH
# ============================================================

def search_bing(
    keyword,
    extension,
    max_pages
):
    urls = set()

    if not BING_ENDPOINT or not BING_API_KEY:
        return urls

    query = (
        f'"{keyword}" '
        f"filetype:{extension}"
    )

    headers = {
        "Ocp-Apim-Subscription-Key":
            BING_API_KEY
    }

    count = 50

    for page in range(max_pages):
        try:
            params = {
                "q": query,
                "count": count,
                "offset": page * count,
            }

            response = requests.get(
                BING_ENDPOINT,
                headers=headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            data = response.json()

            results = (
                data.get("webPages", {})
                .get("value", [])
            )

            if not results:
                break

            new_count = 0

            for item in results:
                url = item.get("url", "").strip()

                if url and urlparse(
                    url
                ).path.lower().endswith(
                    SUPPORTED_TYPES[extension]
                ):
                    if url not in urls:
                        urls.add(url)
                        new_count += 1

            print(
                f"{BLUE}[API SEARCH]{RESET} "
                f"{YELLOW}{keyword}{RESET} | "
                f".{extension} | "
                f"Page {page + 1} | "
                f"New {new_count}"
            )

            if len(results) < count:
                break

        except Exception as error:
            print(
                f"{RED}[API ERROR]{RESET} "
                f"{error}"
            )
            break

    return urls


# ============================================================
# COMMON CRAWL SEARCH
# ============================================================

def search_common_crawl(
    keyword,
    extension
):
    """
    Common Crawl is URL-pattern based rather than a normal
    keyword search engine.

    This function discovers indexed URLs matching the requested
    file extension. For targeted searches, use a domain/pattern
    as the keyword, such as:
        example.com
        *.example.com
    """

    urls = set()

    try:
        index_url = (
            "https://index.commoncrawl.org/"
            f"{COMMON_CRAWL_INDEX}-index"
        )

        domain_pattern = keyword.strip()

        if not domain_pattern:
            return urls

        if not domain_pattern.startswith("*"):
            domain_pattern = (
                f"*.{domain_pattern}"
            )

        query_params = {
            "url": (
                f"{domain_pattern}/*"
                f"{SUPPORTED_TYPES[extension]}"
            ),
            "output": "json",
            "filter": "status:200",
        }

        url = (
            f"{index_url}?"
            f"{urlencode(query_params)}"
        )

        response = requests.get(
            url,
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            return urls

        for line in response.iter_lines(
            decode_unicode=True
        ):
            if not line:
                continue

            try:
                item = json.loads(line)

                found_url = item.get(
                    "url",
                    ""
                ).strip()

                if found_url:
                    urls.add(found_url)

            except Exception:
                continue

        print(
            f"{MAGENTA}[COMMON CRAWL]{RESET} "
            f"{keyword} | "
            f".{extension} | "
            f"URLs: {GREEN}{len(urls)}{RESET}"
        )

    except Exception as error:
        print(
            f"{RED}[COMMON CRAWL ERROR]{RESET} "
            f"{error}"
        )

    return urls


# ============================================================
# COMBINED SEARCH
# ============================================================

def search_all_sources(
    keywords,
    file_types,
    pages,
    threads
):
    all_urls = set()
    lock = threading.Lock()

    jobs = []

    with ThreadPoolExecutor(
        max_workers=threads
    ) as executor:

        for keyword in keywords:
            for extension in file_types:

                if SEARXNG_URL:
                    jobs.append(
                        executor.submit(
                            search_searxng,
                            keyword,
                            extension,
                            pages
                        )
                    )

                if BING_ENDPOINT and BING_API_KEY:
                    jobs.append(
                        executor.submit(
                            search_bing,
                            keyword,
                            extension,
                            pages
                        )
                    )

                # Common Crawl is best with domains/patterns.
                jobs.append(
                    executor.submit(
                        search_common_crawl,
                        keyword,
                        extension
                    )
                )

        for future in as_completed(jobs):
            try:
                results = future.result()

                with lock:
                    all_urls.update(results)

            except Exception as error:
                print(
                    f"{RED}[WORKER ERROR]{RESET} "
                    f"{error}"
                )

    return sorted(all_urls)


# ============================================================
# DOWNLOAD
# ============================================================

_thread_local = threading.local()


def get_session():
    if not hasattr(
        _thread_local,
        "session"
    ):
        session = requests.Session()

        session.headers.update({
            "User-Agent":
                "Mozilla/5.0"
        })

        _thread_local.session = session

    return _thread_local.session


def get_extension(url):
    path = urlparse(url).path.lower()

    for ext in SUPPORTED_TYPES.values():
        if path.endswith(ext):
            return ext

    return None


def safe_download_path(url, ext):
    parsed = urlparse(url)

    filename = os.path.basename(
        parsed.path
    )

    if not filename:
        digest = hashlib.sha256(
            url.encode()
        ).hexdigest()[:16]

        filename = (
            f"file_{digest}{ext}"
        )

    filename = filename.replace(
        "..",
        "_"
    )

    path = DOWNLOAD_DIR / filename

    counter = 2

    while path.exists():
        path = DOWNLOAD_DIR / (
            f"{Path(filename).stem}_{counter}"
            f"{Path(filename).suffix}"
        )

        counter += 1

    return path


def download_file(url):
    ext = get_extension(url)

    if not ext:
        return None

    try:
        session = get_session()

        with session.get(
            url,
            stream=True,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        ) as response:

            response.raise_for_status()

            size = 0

            output = safe_download_path(
                url,
                ext
            )

            with open(
                output,
                "wb"
            ) as file:

                for chunk in response.iter_content(
                    65536
                ):
                    if not chunk:
                        continue

                    size += len(chunk)

                    if size > MAX_FILE_SIZE:
                        file.close()

                        output.unlink(
                            missing_ok=True
                        )

                        print(
                            f"{YELLOW}[SKIP LARGE]{RESET} "
                            f"{url}"
                        )

                        return None

                    file.write(chunk)

            print(
                f"{GREEN}[DOWNLOADED]{RESET} "
                f"{WHITE}{output.name}{RESET}"
            )

            return output

    except Exception as error:
        print(
            f"{RED}[DOWNLOAD ERROR]{RESET} "
            f"{url} -> {error}"
        )

        return None


# ============================================================
# MAIN
# ============================================================

def main():
    logo()

    print(
        f"{GREEN}[SOURCE STATUS]{RESET}"
    )

    print(
        f"  SearXNG: "
        f"{GREEN if SEARXNG_URL else RED}"
        f"{'ENABLED' if SEARXNG_URL else 'DISABLED'}"
    )

    print(
        f"  Common Crawl: "
        f"{GREEN}ENABLED{RESET}"
    )

    print(
        f"  API Search: "
        f"{GREEN if BING_ENDPOINT and BING_API_KEY else RED}"
        f"{'ENABLED' if BING_ENDPOINT and BING_API_KEY else 'DISABLED'}"
    )

    print()

    keywords = get_keywords()
    threads = get_threads()
    pages = get_pages()
    file_types = get_file_types()

    print()
    print(
        f"{CYAN}[STARTING MULTI-SOURCE SEARCH]{RESET}"
    )

    urls = search_all_sources(
        keywords,
        file_types,
        pages,
        threads
    )

    print()
    print(
        f"{GREEN}[SEARCH COMPLETE]{RESET} "
        f"Unique URLs: "
        f"{YELLOW}{len(urls)}{RESET}"
    )

    if not urls:
        return

    url_output = (
        BASE_DIR /
        f"Discovered-URLs[{len(urls)}].txt"
    )

    with open(
        url_output,
        "w",
        encoding="utf-8"
    ) as file:
        for url in urls:
            file.write(url + "\n")

    print(
        f"{GREEN}[SAVED]{RESET} "
        f"{url_output.name}"
    )

    print()
    print(
        f"{CYAN}[STARTING DOWNLOAD]{RESET}"
    )

    downloaded = []

    with ThreadPoolExecutor(
        max_workers=threads
    ) as executor:

        futures = {
            executor.submit(
                download_file,
                url
            ): url
            for url in urls
        }

        total = len(futures)
        completed = 0

        for future in as_completed(futures):
            completed += 1

            try:
                result = future.result()

                if result:
                    downloaded.append(result)

            except Exception as error:
                print(
                    f"{RED}[DOWNLOAD WORKER ERROR]{RESET} "
                    f"{error}"
                )

            print(
                f"{CYAN}[PROGRESS]{RESET} "
                f"{GREEN}{completed}{RESET}/"
                f"{YELLOW}{total}{RESET}"
            )

    print()
    print(
        f"{GREEN}[COMPLETE]{RESET}"
    )

    print(
        f"Unique URLs: "
        f"{YELLOW}{len(urls)}{RESET}"
    )

    print(
        f"Downloaded files: "
        f"{YELLOW}{len(downloaded)}{RESET}"
    )

    print(
        f"Folder: "
        f"{WHITE}{DOWNLOAD_DIR}{RESET}"
    )

    input(
        f"\n{CYAN}Press Enter to exit...{RESET}"
    )


if __name__ == "__main__":
    main()
