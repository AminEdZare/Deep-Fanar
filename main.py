import asyncio
from llm import ask
from datetime import date
import ast

from tools import url_scrape, tavily_search

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
    original_query = "Research recent papers on multi-agent systems" # this is just an example
    # original_query = "What's the newest iPhone?"

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
        queries = await asyncio.gather(*(ask(query_system_prompt, original_query) for query_system_prompt in queries_system_prompts))

        # uncomment this to debug
        print("====QUERIES====")
        print(queries[0])
        print(queries[1])
        
        english_queries.append(queries[0])
        arabic_queries.append(queries[1])

        # -- search the newest queries -- #
        english_search_results = tavily_search(english_queries[-1])
        arabic_search_results = tavily_search(arabic_queries[-1])

        english_urls.append(english_search_results[0])
        english_urls.append(english_search_results[1])

        arabic_urls.append(arabic_search_results[0])
        arabic_urls.append(arabic_search_results[1])

        # uncomment this to debug
        print("====URLS====")
        print(english_urls[-2:])
        print(arabic_urls[-2:])

        # -- scrape the urls -- #
        english_scrapes.append(url_scrape(english_urls[-1]))
        english_scrapes.append(url_scrape(english_urls[-2]))

        arabic_scrapes.append(url_scrape(arabic_urls[-1]))
        arabic_scrapes.append(url_scrape(arabic_urls[-2]))

        # uncomment this to debug
        print("====SCRAPES====")
        print(english_scrapes[-2] + '\n\n' + english_scrapes[-1])
        print(arabic_scrapes[-2] + '\n\n' + arabic_scrapes[-1])


        # -- summarize the scrapes in parallel -- #
        summarize_system_prompts = [
            (summarize_english_system_prompt + f"text: {english_scrapes[-1]}\n"),
            (summarize_english_system_prompt + f"text: {english_scrapes[-2]}\n"),
            (summarize_arabic_system_prompt + f"text: {arabic_scrapes[-1]}\n"),
            (summarize_arabic_system_prompt + f"text: {arabic_scrapes[-2]}\n"),
        ]
        summaries = await asyncio.gather(*(ask(summarize_system_prompt, original_query) for summarize_system_prompt in summarize_system_prompts))

        english_summaries.append(summaries[-4])
        english_summaries.append(summaries[-3])
        arabic_summaries.append(summaries[-2])
        arabic_summaries.append(summaries[-1])

        # uncomment this to debug
        print("====SUMMARIES====")
        print(summaries[-4])
        print(summaries[-3])
        print(summaries[-2])
        print(summaries[-1])
    
    # -- synthesize every summary into a final response -- #
    synthesis = await ask(synthesizer_system_prompt + f"English summaries: {english_summaries}\nArabic summaries: {arabic_summaries}\n", original_query)

    # printing everything
    print("===FINISHED RESEARCHING===")
    print(f"Abstract: \n{synthesis}\n")

    counter = 1
    for en_url, en_sum, ar_url, ar_sum in zip(english_urls, english_summaries, arabic_urls, arabic_summaries):
        print(f"Source {counter} - {en_url}: \n{en_sum}\n")
        counter += 1
        print(f"Source {counter} - {ar_url}: \n{ar_sum}\n")
        counter += 1

    print("===END===")


if __name__ == "__main__":
    asyncio.run(main())