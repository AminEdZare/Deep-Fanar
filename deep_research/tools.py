import requests
from bs4 import BeautifulSoup
import json
from pdfminer.high_level import extract_text
import io
import re

from llm import tavily_client

from llm import GOOGLE_API_KEY, GOOGLE_CX_ID

URL_CHAR_LIMIT = 125 # adjust
MAX_SCRAPE_LENGTH = 5000  # Maximum characters for scraped content
MAX_LLM_CONTENT_LENGTH = 3000  # Maximum characters to send to LLM
MAX_TOKENS_PER_CONTENT = 3000  # Conservative token limit per content piece

# --------------------------------------------------------------------------- #
def estimate_tokens(text: str) -> int:
    """
    Rough estimation of token count. OpenAI uses ~4 characters per token on average.
    This is a conservative estimate to avoid context length issues.
    """
    return len(text) // 4  # More realistic estimate: 4 chars per token

def truncate_for_llm(text: str) -> str:
    """
    Truncate text to ensure it fits within LLM context limits.
    """
    if estimate_tokens(text) <= MAX_TOKENS_PER_CONTENT:
        return text
    
    # Truncate to fit within token limit
    max_chars = MAX_TOKENS_PER_CONTENT * 4  # Convert back to character limit
    return text[:max_chars] + "..."

def is_corrupted_content(text: str) -> bool:
    """
    Check if scraped content is corrupted or has encoding issues.
    Returns True if content should be filtered out.
    """
    if not text or len(text.strip()) == 0:
        return True
    
    # Check for excessive encoding artifacts (like Ø£Ù\x84ØªØ±Ø§Ù\x84Ù\x8aØªÙ\x8aÙ\x83Ø³)
    encoding_artifacts = re.findall(r'[ØÙ\x8a\x8b\x8c\x8d\x8e\x8f]+', text)
    if len(encoding_artifacts) > 10:  # If there are many encoding artifacts
        return True
    
    # Check for excessive non-printable characters
    non_printable_ratio = len(re.findall(r'[^\x20-\x7E\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text)) / len(text)
    if non_printable_ratio > 0.3:  # If more than 30% are non-printable
        return True
    
    # Check for excessive repeated characters (like spam or corrupted content)
    repeated_chars = re.findall(r'(.)\1{10,}', text)  # Same character repeated 11+ times
    if len(repeated_chars) > 5:
        return True
    
    return False

def is_content_too_long(text: str) -> bool:
    """
    Check if content is too long for LLM processing.
    """
    return estimate_tokens(text) > MAX_TOKENS_PER_CONTENT

def is_usable_content(text: str) -> bool:
    """
    Comprehensive check for whether content is usable for LLM processing.
    """
    if is_corrupted_content(text):
        return False
    
    # Don't reject content that's too long - let truncation handle that
    # if is_content_too_long(text):
    #     return False
    
    # Check if content has meaningful text (not just whitespace, numbers, or symbols)
    meaningful_chars = re.findall(r'[a-zA-Z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text)
    if len(meaningful_chars) < 50:  # Need at least 50 meaningful characters
        return False
    
    return True

def prepare_content_for_llm(text: str) -> str:
    """
    Prepare content for LLM processing by truncating if necessary.
    """
    if not is_usable_content(text):
        return ""
    
    return truncate_for_llm(text)

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
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        # ------------ PDF or HTML? ---------------------------------
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
        
        # Apply length limit
        if len(text) > MAX_SCRAPE_LENGTH:
            text = text[:MAX_SCRAPE_LENGTH]
        
        # Validate content quality
        if not is_usable_content(text):
            return f"Failed to scrape usable content from {url}: Content is corrupted, too long, or lacks meaningful text"
        
        return text

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