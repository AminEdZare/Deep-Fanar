import requests
from bs4 import BeautifulSoup

from llm import tavily_client

# --------------------------------------------------------------------------- #
def url_scrape(url: str) -> str:
    """
    Scrapes a website for its contents given a URL.
    """
    try:    
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
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
        return [item['url'] for item in response['results']]
    except Exception as e:
        return [f"Search failed: {str(e)}"]