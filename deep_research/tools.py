import requests
from bs4 import BeautifulSoup
import json
from pdfminer.high_level import extract_text
import io

from llm import tavily_client

from llm import GOOGLE_API_KEY, GOOGLE_CX_ID

URL_CHAR_LIMIT = 125 # adjust

# --------------------------------------------------------------------------- #
def url_scrape(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()

        # ------------ PDF or HTML? ---------------------------------
        ctype = (r.headers.get("Content-Type") or "").lower()
        is_pdf_header = r.content[:4] == b"%PDF"
        is_pdf_url    = url.lower().endswith(".pdf")
        is_pdf        = ("application/pdf" in ctype) or is_pdf_url or is_pdf_header

        if is_pdf:
            # ----------- PDF branch --------------------------------
            text = extract_text(io.BytesIO(r.content)) or ""
        else:
            # ----------- HTML branch -------------------------------
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = " ".join(soup.stripped_strings)

        text = text.strip()
        return text[:5000] if len(text) > 5000 else text

    except Exception as e:
        return f"Failed to scrape content from {url}: {e}"
    
# --------------------------------------------------------------------------- #
def tavily_search(query: str) -> list[str]:
    try:
        response = tavily_client.search(
            query=query, 
            max_results=2, 
            exclude_domains=["sciencedirect.com"]
            )
        urls = []
        for item in response["results"]:
            url = item["url"]
            if len(url) > URL_CHAR_LIMIT:
                url = shorten_url(url)
            urls.append(url)
        return urls
    except Exception as e:
        return [f"Tavily search failed: {str(e)}"]

# --------------------------------------------------------------------------- #
def google_search(query: str) -> list[str]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx":  GOOGLE_CX_ID,
        "q":   query,
        "num": 2
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        urls = []
        for item in data.get("items", []):
            link = item["link"]
            if len(link) > URL_CHAR_LIMIT:
                link = shorten_url(link)
            urls.append(link)
        return urls or ["No results returned by Google."]
    except Exception as e:
        return [f"Google search failed: {e}"]
    
# --------------------------------------------------------------------------- #
def shorten_url(long_url: str) -> str:
    api_url = "https://is.gd/create.php"
    params = {
        'format': 'json',
        'url': long_url
    }
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()  # for bad status codes
        data = response.json()
        if 'shorturl' in data:
            return data['shorturl']
        else:
            # is.gd returns an 'errorcode' and 'errormessage' on failure
            error_message = data.get('errormessage', 'Unknown error')
            return f"Failed to shorten URL. Reason: {error_message}"
    except requests.exceptions.RequestException as e:
        return f"Request to is.gd failed: {str(e)}"
    except json.JSONDecodeError:
        return "Failed to parse response from is.gd. The service might be down."