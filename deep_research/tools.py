import requests
from bs4 import BeautifulSoup
import json

from llm import tavily_client

from llm import GOOGLE_API_KEY, GOOGLE_CX_ID

URL_CHAR_LIMIT = 125 # adjust

# --------------------------------------------------------------------------- #
def url_scrape(url: str) -> str:
    """
    Scrapes a website for its contents given a URL.
    """
    try:    
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text(separator=' ', strip=True)
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        # Limit to 5000 characters from scrape
        return text[:5000] if len(text) > 5000 else text
    except Exception as e:
        return f"Failed to scrape content from {url}: {str(e)}"
    
# --------------------------------------------------------------------------- #
def tavily_search(query: str) -> list[str]:
    try:
        response = tavily_client.search(query=query, max_results=2)
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