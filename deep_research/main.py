import asyncio
from llm import ask
from datetime import date
import re

from tools import url_scrape, tavily_search, google_search, shorten_url

from prompts import (
    planner_system_prompt,

    english_queries_system_prompt,
    arabic_queries_system_prompt,

    summarize_english_system_prompt,
    summarize_arabic_system_prompt,

    synthesizer_system_prompt
)

async def main() -> None:
    #original_query = input("User: ")
    #original_query = "Research recent papers on multi-agent systems" # this is just an example
    #original_query = "What's the newest iPhone?"
    #original_query = "What are the health benefits and potential side effects of drinking green tea?"
    original_query = "Given the AI boom, how can engineers stay ahead of the curve other than mastering AI prompting"
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

    # -- determine number of loops -- #
    number_of_loops = int(await ask(planner_system_prompt, original_query))

    if number_of_loops not in [1, 2, 3, 4, 5, 6]:
        print("error: number_of_loops not in [1, 2, 3, 4, 5, 6]")
    else:
        print(f"number_of_loops = {number_of_loops}")

    for i in range(number_of_loops):
        print(f"\n--- Starting Research Loop {i+1}/{number_of_loops} ---")
        # -- generate queries -- #
        queries_system_prompts = [(english_queries_system_prompt +
                                   f"Already searched queries: {english_queries}\n" +
                                   f"Current summaries: {english_summaries}"),

                                    (arabic_queries_system_prompt +
                                    f"Already searched queries: {arabic_queries}\n" +
                                    f"Current summaries: {arabic_summaries}")]

        # runs both ask function calls in parallel
        queries = await asyncio.gather(*(ask(query_system_prompt, temp_new_query) for query_system_prompt in queries_system_prompts))

        temp_new_query = "Write a follow-up query." # reset

        print("====QUERIES====")
        print(f"English Query: {queries[0]}")
        print(f"Arabic Query: {queries[1]}")

        english_queries.append(queries[0])
        arabic_queries.append(queries[1])

        # -- search the newest queries -- #
        new_en_urls = tavily_search(english_queries[-1])[:2]   # ≤2
        new_ar_urls = google_search(arabic_queries[-1])[:2]     # ≤2

        # -- scrape the new URLs, keeping only successful ones -- #
        good_en_urls, good_en_scrapes = [], []
        bad_en_urls, bad_en_scrapes = [], []
        for url in new_en_urls:
            scrape = url_scrape(url)
            if scrape.startswith("Failed to scrape content"):
                bad_en_urls.append(url)
                bad_en_scrapes.append(scrape)
                continue
            good_en_urls.append(url)
            good_en_scrapes.append(scrape)

        good_ar_urls, good_ar_scrapes = [], []
        bad_ar_urls, bad_ar_scrapes = [], []
        for url in new_ar_urls:
            scrape = url_scrape(url)
            if scrape.startswith("Failed to scrape content"):
                bad_ar_urls.append(url)
                bad_ar_scrapes.append(scrape)
                continue
            good_ar_urls.append(url)
            good_ar_scrapes.append(scrape)

        english_urls.extend(good_en_urls)
        arabic_urls.extend(good_ar_urls)
        english_scrapes.extend(good_en_scrapes)
        arabic_scrapes.extend(good_ar_scrapes)

        # -- summarize the scrapes in parallel -- #
        summarize_system_prompts = (
            [summarize_english_system_prompt + f"text: {s}\n" for s in good_en_scrapes] +
            [summarize_arabic_system_prompt  + f"text: {s}\n" for s in good_ar_scrapes]
        )
        summaries = await asyncio.gather(*(ask(summarize_system_prompt, temp_summary_query) for summarize_system_prompt in summarize_system_prompts))
        temp_summary_query = "Write a summary."

        en_count = len(good_en_scrapes)
        english_summaries.extend(summaries[:en_count])
        arabic_summaries.extend(summaries[en_count:])

        print("====SUMMARIES====")
        if summaries[:en_count]:
            print("English Summaries:")
            for summary in summaries[:en_count]:
                print(f"- {summary[:100]}...")
        if summaries[en_count:]:
            print("\nArabic Summaries:")
            for summary in summaries[en_count:]:
                print(f"- {summary[:100]}...")

    # -- Combine all summaries and their URLs for the synthesizer -- #
    all_sources = []
    # Combine English summaries with their URLs
    for i in range(len(english_summaries)):
        all_sources.append(f"Source: [{english_urls[i]}]\nSummary: {english_summaries[i]}")

    # Combine Arabic summaries with their URLs
    for i in range(len(arabic_summaries)):
        all_sources.append(f"Source: [{arabic_urls[i]}]\nSummary: {arabic_summaries[i]}")

    # -- synthesize every summary into a final response -- #
    synthesis_prompt_input = (
        synthesizer_system_prompt +
        f"Sources:\n" +
        "\n\n".join(all_sources)
    )

    synthesis = await ask(synthesis_prompt_input, original_query)
    synthesis_clean = re.sub(r"<think>.*?</think>", "", synthesis, flags=re.DOTALL).strip()

    # -- All successful URLs are now cited inline in the synthesis -- #

    # printing the final research paper
    print("\n\n=== RESEARCH PAPER ===")
    print(f"Query: {original_query}\n")
    print(synthesis_clean)

    # The separate "REFERENCES" section is no longer needed.

    print("\n===END===")


if __name__ == "__main__":
    asyncio.run(main())