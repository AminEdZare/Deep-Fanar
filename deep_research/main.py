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
    original_query = "Can recent discoveries in brain plasticity and connectome mapping reshape how we train reinforcement learning models?"
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

    for _ in range(number_of_loops):
        # -- generate queries -- #


        # todo: change the example queries here into actual Arabic queries


        queries_system_prompts = [(english_queries_system_prompt +
                                   f"Already searched queries: {english_queries}\n" +
                                   f"Current summaries: {english_summaries}"),
                                   
                                    (arabic_queries_system_prompt +
                                    f"Already searched queries: {arabic_queries}\n" +
                                    f"Current summaries: {arabic_summaries}")]

        # runs both ask function calls in parallel
        queries = await asyncio.gather(*(ask(query_system_prompt, temp_new_query) for query_system_prompt in queries_system_prompts))

        temp_new_query = "Write a follow-up query." # reset

        # uncomment this to debug
        print("====QUERIES====")
        print(queries[0])
        print(queries[1])
        
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
                # still keeping bad for maintenance
                bad_en_urls.append(url)
                bad_en_scrapes.append(scrape)
                continue              # skip bad English scrape
            good_en_urls.append(url)
            good_en_scrapes.append(scrape)

        good_ar_urls, good_ar_scrapes = [], []
        bad_ar_urls, bad_ar_scrapes = [], []
        for url in new_ar_urls:
            scrape = url_scrape(url)
            if scrape.startswith("Failed to scrape content"):
                # still keeping bad for maintenance
                bad_ar_urls.append(url)
                bad_ar_scrapes.append(scrape)
                continue              # skip bad Arabic scrape
            good_ar_urls.append(url)
            good_ar_scrapes.append(scrape)

        # -- store only successful results -- #
        english_urls.extend(good_en_urls)
        arabic_urls.extend(good_ar_urls)
        english_scrapes.extend(good_en_scrapes)
        arabic_scrapes.extend(good_ar_scrapes)
        
        # uncomment this to debug
        print("====SCRAPES====")
        print(good_en_scrapes, "\n")
        print(good_ar_scrapes, "\n")
        print(bad_en_scrapes, "\n")
        print(bad_ar_scrapes, "\n")

        # -- summarize the scrapes in parallel -- #
        summarize_system_prompts = (
            [summarize_english_system_prompt + f"text: {s}\n" for s in good_en_scrapes] +
            [summarize_arabic_system_prompt  + f"text: {s}\n" for s in good_ar_scrapes]
        )
        summaries = await asyncio.gather(*(ask(summarize_system_prompt, temp_summary_query) for summarize_system_prompt in summarize_system_prompts))
        temp_summary_query = "Write a summary."

        # first `new_en_scrapes` are EN; rest AR
        en_count = len(good_en_scrapes)
        english_summaries.extend(summaries[:en_count])
        arabic_summaries.extend(summaries[en_count:])

        # uncomment this to debug
        print("====SUMMARIES====")
        print(summaries[:en_count], "\n")
        print(summaries[en_count:])
    
    # -- synthesize every summary into a final response -- #
    synthesis = await ask(synthesizer_system_prompt + 
                          f"English summaries: {english_summaries}\nArabic summaries: {arabic_summaries}\n", 
                          original_query)
    # clean up unwanted tags like <think>...</think>
    synthesis_clean = re.sub(r"<think>.*?</think>", "", synthesis, flags=re.DOTALL).strip()

    # printing everything
    print("===FINISHED RESEARCHING===")
    print(f"Overall summary: \n{synthesis_clean}\n")

    # interweave
    en_counter = 0
    ar_counter = 0
    while(en_counter < len(english_urls) and ar_counter < len(arabic_urls)):
        print(f"English source {en_counter + 1} - {english_urls[en_counter]}: \n{english_summaries[en_counter]}\n")
        en_counter += 1
        print(f"Arabic source {ar_counter + 1} - {arabic_urls[ar_counter]}: \n{arabic_summaries[ar_counter]}\n")
        ar_counter += 1
    # flush
    while (en_counter < len(english_urls)):
        print(f"English source {en_counter + 1} - {english_urls[en_counter]}: \n{english_summaries[en_counter]}\n")
        en_counter += 1
    while(ar_counter < len(arabic_urls)):
        print(f"Arabic source {ar_counter + 1} - {arabic_urls[ar_counter]}: \n{arabic_summaries[ar_counter]}\n")
        ar_counter += 1

    print("===END===")


if __name__ == "__main__":
    asyncio.run(main())