from scraping_functions import CoinGeckoScraper

# you can change the "3" in the link to scrape whatever page you're interested in
cg_scraper = CoinGeckoScraper("https://www.coingecko.com/?page=3")
cg_scraper.process_all_tokens(max_tokens=101)
