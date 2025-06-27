# deep_research/main.py — minimal debug prints only

import asyncio
import re
from datetime import date  # kept for possible future use
import json  # kept for possible future use

from llm import ask
from tools import url_scrape, tavily_search, google_search, is_usable_content, prepare_content_for_llm
from prompts import (
    planner_system_prompt,
    english_queries_system_prompt,
    arabic_queries_system_prompt,
    summarize_english_system_prompt,
    summarize_arabic_system_prompt,
    synthesizer_system_prompt,
)


async def run_research(original_query: str):
    """Orchestrate multilingual web‑research with progress events.

    Only *additional* behaviour beyond the original version is a handful of
    print statements for lightweight debugging. No other logic changed.
    """

    # ------------------------------------------------------------
    # INITIAL SETUP
    # ------------------------------------------------------------
    print(f"[DEBUG] Starting run_research with query: {original_query}")
    yield {"type": "progress", "stage": "Planning research strategy...", "detail": ""}

    temp_new_query = original_query
    temp_summary_query = original_query

    number_of_loops: int = 0

    # Language‑specific buffers
    english_queries: list[str] = []
    arabic_queries: list[str] = []

    english_urls: list[str] = []
    arabic_urls: list[str] = []

    english_scrapes: list[str] = []
    arabic_scrapes: list[str] = []

    english_summaries: list[str] = []
    arabic_summaries: list[str] = []

    # ------------------------------------------------------------
    # 1) DETERMINE LOOP COUNT
    # ------------------------------------------------------------
    number_of_loops_str = await ask(planner_system_prompt, original_query)
    try:
        number_of_loops = int(number_of_loops_str)
    except ValueError:
        print(
            f"Warning: Planner returned non‑integer '{number_of_loops_str}'. "
            "Defaulting to 1 loop."
        )
        number_of_loops = 1

    if not (1 <= number_of_loops <= 6):
        print(
            f"Warning: number_of_loops ({number_of_loops}) out of expected range [1, 6]. "
            "Adjusting."
        )
        number_of_loops = max(1, min(6, number_of_loops))

    print(f"[DEBUG] Running {number_of_loops} research loop(s)")
    yield {
        "type": "progress",
        "stage": f"Determined {number_of_loops} research loops.",
        "detail": "",
    }

    # ------------------------------------------------------------
    # 2) MAIN LOOP
    # ------------------------------------------------------------
    for i in range(number_of_loops):
        loop_idx = i + 1
        yield {
            "type": "progress",
            "stage": "Generating search queries...",
            "detail": f"{loop_idx}/{number_of_loops}",
        }

        # Compose system prompts
        queries_system_prompts = [
            english_queries_system_prompt
            + f"Already searched queries: {english_queries}\n"
            + f"Current summaries: {english_summaries}",
            arabic_queries_system_prompt
            + f"Already searched queries: {arabic_queries}\n"
            + f"Current summaries: {arabic_summaries}",
        ]

        queries = await asyncio.gather(
            *(ask(q_prompt, temp_new_query) for q_prompt in queries_system_prompts)
        )
        
        # ── NEW: strip wrapping quotes ("" or ''), keep internal quotes intact ──
        queries = [
            q[1:-1].strip() if len(q) > 1 and q[0] == q[-1] and q[0] in "\"'" else q.strip()
            for q in queries
        ]

        print(
            f"[DEBUG] Loop {loop_idx}: EN query = {queries[0]} | "
            f"AR query = {queries[1]}"
        )

        temp_new_query = "Write a follow‑up query."  # placeholder so LLM varies

        # --------------------------------------------------------
        # 2a) SEARCH & SCRAPE
        # --------------------------------------------------------
        yield {
            "type": "progress",
            "stage": "Searching and scraping sources...",
            "detail": f"{loop_idx}/{number_of_loops}",
        }

        english_queries.append(queries[0])
        arabic_queries.append(queries[1])

        new_en_urls = tavily_search(english_queries[-1])[:2]
        new_ar_urls = google_search(arabic_queries[-1])[:2]

        good_en_urls, good_en_scrapes = [], []
        bad_en_urls, bad_en_scrapes = [], []
        for url in new_en_urls:
            scrape = url_scrape(url)
            if scrape and is_usable_content(scrape):
                good_en_urls.append(url)
                good_en_scrapes.append(prepare_content_for_llm(scrape))
            else:
                bad_en_urls.append(url)
                bad_en_scrapes.append(scrape)

        good_ar_urls, good_ar_scrapes = [], []
        bad_ar_urls, bad_ar_scrapes = [], []
        for url in new_ar_urls:
            scrape = url_scrape(url)
            if scrape and is_usable_content(scrape):
                good_ar_urls.append(url)
                good_ar_scrapes.append(prepare_content_for_llm(scrape))
            else:
                bad_ar_urls.append(url)
                bad_ar_scrapes.append(scrape)

        english_urls.extend(good_en_urls)
        arabic_urls.extend(good_ar_urls)
        english_scrapes.extend(good_en_scrapes)
        arabic_scrapes.extend(good_ar_scrapes)

        

        print(
            f"[DEBUG] Loop {loop_idx}: good_en={good_en_urls} "
            f"good_ar={good_ar_urls}"
        )

        print(
            f"[DEBUG] Loop {loop_idx}: good_en_scrapes={good_en_scrapes} "
            f"good_ar_scrapes={good_ar_scrapes}"
        )

        # --------------------------------------------------------
        # 2b) SUMMARIZATION
        # --------------------------------------------------------
        yield {
            "type": "progress",
            "stage": "Summarizing scraped content...",
            "detail": f"Found {len(good_en_scrapes) + len(good_ar_scrapes)} new sources.",
        }

        summarize_system_prompts = (
            [summarize_english_system_prompt + f"text: {s}\n" for s in good_en_scrapes]
            + [summarize_arabic_system_prompt + f"text: {s}\n" for s in good_ar_scrapes]
        )

        if not summarize_system_prompts:
            yield {
                "type": "progress",
                "stage": "No new content to summarize for this loop.",
                "detail": "",
            }
            continue

        summaries = await asyncio.gather(
            *(ask(s_prompt, temp_summary_query) for s_prompt in summarize_system_prompts)
        )
        temp_summary_query = "Write a summary."  # placeholder

        en_count = len(good_en_scrapes)
        english_summaries.extend(summaries[:en_count])
        arabic_summaries.extend(summaries[en_count:])

    # ------------------------------------------------------------
    # 3) FINAL SYNTHESIS
    # ------------------------------------------------------------
    yield {"type": "progress", "stage": "Composing final research paper...", "detail": ""}

    all_sources = []
    for idx, summary in enumerate(english_summaries):
        url_citation = english_urls[idx] if idx < len(english_urls) else "No URL available"
        all_sources.append(f"Source: [{url_citation}]\nSummary: {summary}")
    for idx, summary in enumerate(arabic_summaries):
        url_citation = arabic_urls[idx] if idx < len(arabic_urls) else "No URL available"
        all_sources.append(f"Source: [{url_citation}]\nSummary: {summary}")

    if not all_sources:
        synthesis_clean = (
            "No relevant information could be found or summarized for your query. "
            "Please try a different query."
        )
    else:
        synthesis_prompt_input = (
            synthesizer_system_prompt + "Sources:\n" + "\n\n".join(all_sources)
        )
        synthesis = await ask(synthesis_prompt_input, original_query)
        synthesis_clean = re.sub(r"<think>.*?</think>", "", synthesis, flags=re.DOTALL).strip()

    print(f"[DEBUG] Final synthesis length: {len(synthesis_clean)} characters")
    
    # Combine all URLs from both languages and remove duplicates while preserving order
    seen_urls = set()
    all_visited_urls = []
    
    # Add English URLs first (maintaining their order)
    for url in english_urls:
        if url not in seen_urls:
            all_visited_urls.append(url)
            seen_urls.add(url)
    
    # Add Arabic URLs (maintaining their order, skipping duplicates)
    for url in arabic_urls:
        if url not in seen_urls:
            all_visited_urls.append(url)
            seen_urls.add(url)
    
    yield {
        "type": "final", 
        "content": synthesis_clean,
        "sources": all_visited_urls
    }
