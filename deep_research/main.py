# deep_research/main.py (MODIFIED FOR CONCISE PROGRESS)

import asyncio
import re
from datetime import date 
import json 

from llm import ask
from tools import url_scrape, tavily_search, google_search, shorten_url
from prompts import (
    planner_system_prompt,
    english_queries_system_prompt,
    arabic_queries_system_prompt,
    summarize_english_system_prompt,
    summarize_arabic_system_prompt,
    synthesizer_system_prompt
)

async def run_research(original_query: str):
    yield {"type": "progress", "stage": "Planning research strategy...", "detail": ""}
    
    temp_new_query = original_query
    temp_summary_query = original_query

    number_of_loops: int = 0

    english_queries: list[str] = []
    arabic_queries: list[str] = []

    english_urls: list[str] = []
    arabic_urls: list[str] = []

    english_scrapes: list[str] = []
    arabic_scrapes: list[str] = []

    english_summaries: list[str] = []
    arabic_summaries: list[str] = []

    number_of_loops_str = await ask(planner_system_prompt, original_query)
    try:
        number_of_loops = int(number_of_loops_str)
    except ValueError:
        print(f"Warning: Planner returned non-integer '{number_of_loops_str}'. Defaulting to 1 loop.")
        number_of_loops = 1 

    if not (1 <= number_of_loops <= 6):
        print(f"Warning: number_of_loops ({number_of_loops}) out of expected range [1, 6]. Adjusting.")
        number_of_loops = max(1, min(6, number_of_loops)) 

    yield {"type": "progress", "stage": f"Determined {number_of_loops} research loops.", "detail": ""}

    for i in range(number_of_loops):
        yield {"type": "progress", "stage": "Generating search queries...", "detail": f"{i+1}/{number_of_loops}"}
        
        queries_system_prompts = [(english_queries_system_prompt +
                                   f"Already searched queries: {english_queries}\n" +
                                   f"Current summaries: {english_summaries}"),
                                  (arabic_queries_system_prompt +
                                   f"Already searched queries: {arabic_queries}\n" +
                                   f"Current summaries: {arabic_summaries}")]

        queries = await asyncio.gather(*(ask(query_system_prompt, temp_new_query) for query_system_prompt in queries_system_prompts))

        temp_new_query = "Write a follow-up query." 

        # MODIFIED: Concise detail for scraping stage
        yield {"type": "progress", "stage": "Searching and scraping sources...", "detail": f"{i+1}/{number_of_loops}"} 

        english_queries.append(queries[0])
        arabic_queries.append(queries[1])

        new_en_urls = tavily_search(english_queries[-1])[:2]  
        new_ar_urls = google_search(arabic_queries[-1])[:2]    

        good_en_urls, good_en_scrapes = [], []
        bad_en_urls, bad_en_scrapes = [], [] 
        for url in new_en_urls:
            scrape = url_scrape(url)
            if scrape and not scrape.startswith("Failed to scrape content"):
                good_en_urls.append(url)
                good_en_scrapes.append(scrape)
            else:
                bad_en_urls.append(url)
                bad_en_scrapes.append(scrape)

        good_ar_urls, good_ar_scrapes = [], []
        bad_ar_urls, bad_ar_scrapes = [], []
        for url in new_ar_urls:
            scrape = url_scrape(url)
            if scrape and not scrape.startswith("Failed to scrape content"):
                good_ar_urls.append(url)
                good_ar_scrapes.append(scrape)
            else:
                bad_ar_urls.append(url)
                bad_ar_scrapes.append(scrape)

        english_urls.extend(good_en_urls)
        arabic_urls.extend(good_ar_urls)
        english_scrapes.extend(good_en_scrapes)
        arabic_scrapes.extend(good_ar_scrapes)

        yield {"type": "progress", "stage": "Summarizing scraped content...", "detail": f"Found {len(good_en_scrapes) + len(good_ar_scrapes)} new sources."}
        
        summarize_system_prompts = (
            [summarize_english_system_prompt + f"text: {s}\n" for s in good_en_scrapes] +
            [summarize_arabic_system_prompt  + f"text: {s}\n" for s in good_ar_scrapes]
        )

        if not summarize_system_prompts:
            yield {"type": "progress", "stage": "No new content to summarize for this loop.", "detail": ""}
            continue 

        summaries = await asyncio.gather(*(ask(summarize_system_prompt, temp_summary_query) for summarize_system_prompt in summarize_system_prompts))
        temp_summary_query = "Write a summary." 

        en_count = len(good_en_scrapes)
        english_summaries.extend(summaries[:en_count])
        arabic_summaries.extend(summaries[en_count:])

    yield {"type": "progress", "stage": "Composing final research paper...", "detail": ""}

    all_sources = []
    for i in range(len(english_summaries)):
        url_citation = english_urls[i] if i < len(english_urls) else "No URL available"
        all_sources.append(f"Source: [{url_citation}]\nSummary: {english_summaries[i]}")

    for i in range(len(arabic_summaries)):
        url_citation = arabic_urls[i] if i < len(arabic_urls) else "No URL available"
        all_sources.append(f"Source: [{url_citation}]\nSummary: {arabic_summaries[i]}")

    if not all_sources:
        synthesis_clean = "No relevant information could be found or summarized for your query. Please try a different query."
    else:
        synthesis_prompt_input = (
            synthesizer_system_prompt +
            f"Sources:\n" +
            "\n\n".join(all_sources)
        )
        synthesis = await ask(synthesis_prompt_input, original_query)
        synthesis_clean = re.sub(r"<think>.*?</think>", "", synthesis, flags=re.DOTALL).strip()

    yield {"type": "final", "content": synthesis_clean}
