from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import urljoin
from datetime import datetime, date
import time
import re
import json


class CoinGeckoScraper:
    def __init__(self, page_url):
        self.page_url = page_url
        self.driver = webdriver.Chrome()
        self.driver.get(self.page_url)
        self.driver.implicitly_wait(10)
    def get_page_content(self):
        html_content = self.driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup

    def wait_for_element(self, by, value, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def navigate_to_next_token_page_and_click_max_button(self):
        self.driver.refresh()
        time.sleep(0.75)
        button = self.wait_for_element(By.CLASS_NAME, 'graph-stats-btn-max', timeout=20)
        self.driver.execute_script("arguments[0].scrollIntoView();", button)
        button.click()

    def scrape_individual_token_page(self, token_url):
        self.driver.get(token_url)

        while True:
            # click all time button
            self.click_all_time_button()

            # get the current page's soup
            page_soup = self.get_current_page_soup()

            # extract the date text from the page
            date_text = self.extract_date_text(page_soup)

            # convert the date text to a date object
            formatted_date = self.convert_to_date(date_text)

            # if the date is not today, break out of the loop and move on. if the date is today, the program did not catch the correct inception date
            if not self.is_today(formatted_date):
                break

            # if the date is today, print a message and continue to the next iteration
            print("date is today, trying again...")

        # return the final HTML soup of the page
        return page_soup

    def click_all_time_button(self):
        button = self.wait_for_element(By.CLASS_NAME, 'graph-stats-btn-max', timeout=10)
        self.driver.execute_script("arguments[0].scrollIntoView();", button)
        time.sleep(1.5)
        while True:
            try:
                # click the max button
                button.click()
                # break out of loop if success
                break
            except ElementClickInterceptedException:
                # handle the confirmation dialogue box
                print("clicking anywhere on the page to handle the confirmation dialogue box")
                self.handle_confirmation_dialog()
        time.sleep(1.5)

    def handle_confirmation_dialog(self):
        # clicking anywhere on the page to dismiss the confirmation dialog
        actions = ActionChains(self.driver)
        actions.move_by_offset(50, 50).click().perform()

    def get_current_page_soup(self):
        page_html_content = self.driver.page_source
        return BeautifulSoup(page_html_content, 'html.parser')

    def extract_date_text(self, page_soup):
        date_element = page_soup.find('g', class_='highcharts-range-input').find('text')
        if date_element:
            return date_element.get_text(strip=True)
        else:
            print("Error: Unable to find date element. Reloading...")
            return None

    def calculate_age(self, formatted_date):
        today = date.today()
        age_in_days = (today - formatted_date).days
        age_in_years = age_in_days / 365
        return age_in_days, age_in_years

    def token_age(self, formatted_date):
        age_in_days, age_in_years = self.calculate_age(formatted_date)
        return age_in_years

    # you can change the ages as needed
    def token_age_description(self, formatted_date):
        age_in_days, age_in_years = self.calculate_age(formatted_date)
        if age_in_years > 4:
            return "Ancient"
        elif 3 <= age_in_years <= 4:
            return "Very Old"
        elif 2 <= age_in_years <= 3:
            return "Old"
        elif 1.5 <= age_in_years < 2:
            return "New"
        elif 1 <= age_in_years < 1.5:
            return "Very New"
        else:
            return "Extremely New"

    def load_existing_data(self, filename='output.txt'):
        try:
            with open(filename, 'r') as txt_file:
                existing_data = json.load(txt_file)
        except FileNotFoundError:
            existing_data = []
        return existing_data

    # save as a txt file so that we can manipulate the data in the filter_tokens.py file
    def save_to_txt(self, data, filename='output.txt'):
        with open(filename, 'w') as txt_file:
            json.dump(data, txt_file, indent=2)

    def process_all_tokens(self, max_tokens=None):
        soup = self.get_page_content()
        table = soup.find('table', {'data-coin-index-target': 'table', 'data-controller': 'coin-row-ads'})

        if table:
            result_data = self.process_token_rows(table, max_tokens)

            # load existing data from the text file
            existing_data = self.load_existing_data()

            # create a set of existing token names for quick lookup
            existing_token_names = set(token_data.get('Token', '') for token_data in existing_data)

            # check for duplicates and update the data
            for new_token_data in result_data:
                new_token_name = new_token_data.get('Token', '')
                if new_token_name in existing_token_names:
                    # Update existing data
                    for i, token_data in enumerate(existing_data):
                        if token_data.get('Token', '') == new_token_name:
                            existing_data[i] = new_token_data
                            break
                else:
                    # add new data to list
                    existing_data.append(new_token_data)

            # save the updated data to a text file
            self.save_to_txt(existing_data, 'output.txt')

        self.driver.quit()

    def process_token_rows(self, table, max_tokens=None):
        result_data = []
        tbody = table.find('tbody')

        for i, row in enumerate(tbody.find_all('tr')):
            if max_tokens is not None and i >= max_tokens:
                # stop processing after reaching the specified number of tokens
                break

            # increment the counter
            i += 1

            # print the progress
            ordinal_suffix = "th" if 11 <= i <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(i % 10, "th")
            print(f"{i}{ordinal_suffix} token processed")

            token_full_url = self.get_token_full_url(row)
            token_page_soup = self.scrape_individual_token_page(token_full_url)
            token_name_tag = token_page_soup.find('span',
                                                  class_='tw-font-bold tw-text-gray-900 dark:tw-text-moon-50 tw-text-lg '
                                                         'md:tw-text-xl tw-leading-7 tw-ml-2 tw-mr-1')
            token_price_tag = token_page_soup.find('span',
                                                   class_="tw-text-gray-900 dark:tw-text-white tw-text-3xl")
            market_cap_tag = token_page_soup.find('span',
                                                  class_='tw-text-gray-900 dark:tw-text-white tw-font-medium')
            token_category_tags = token_page_soup.find_all('span', class_='tw-truncate')

            # check if token_category_tags is not empty
            if token_category_tags:
                # select the last tw-truncate element which is the category for the tokens. eg - AI, DEX, Governance
                token_category_tag = token_category_tags[-1]

                if "ecosystem" in token_category_tag.get_text(strip=True).lower():
                    token_category = "N/A"
                else:
                    token_category = token_category_tag.get_text(strip=True)
            else:
                # if no tw-truncate element or "category" found, set category to "N/A"
                # coingecko probably just hasn't updated
                token_category = "N/A"

            token_name = token_name_tag.get_text(strip=True)
            token_price_text = token_price_tag.get_text(strip=True)
            token_price = float(token_price_text.replace('$', '').replace(',', ''))
            market_cap_text = market_cap_tag.get_text(strip=True)
            market_cap = float(market_cap_text.replace('$', '').replace(',', ''))
            date_text = self.extract_date_text(token_page_soup)

            # calculate token age
            formatted_date = self.convert_to_date(date_text)
            age = self.token_age(formatted_date)
            age_description = self.token_age_description(formatted_date)

            # add all token data to the list as a dictionary
            result_data.append({
                'Token': token_name,
                'Price': token_price,
                'Marketcap': market_cap,
                'Inception_Date': date_text,
                'Token_Category': token_category,
                'Age': f'{age:.2f} years' if age is not None else None,
                'Age_Description': age_description,
            })

        # convert the list to JSON
        json_data = json.dumps(result_data, indent=2)
        return result_data

    def get_token_full_url(self, row):
        cells = row.find_all('td')
        td_element = cells[2]
        individual_token = td_element.find('a')
        href_value = individual_token.get('href')
        return urljoin(self.page_url, href_value)

    def convert_to_date(self, date_text):
        date_match = re.search(r'\b(\w{3}\s+\d{1,2},\s+\d{4})\b', date_text)
        if date_match:
            try:
                formatted_date = datetime.strptime(date_match.group(1), "%b %d, %Y").date()
                return formatted_date
            except Exception as e:
                print(f"Error: Unable to parse date. Exception: {e}. Date Text: {date_text}")
                return None
        else:
            print(f"Error: Unable to find a valid date match. Date Text: {date_text}")
            return None

    def is_today(self, formatted_date):
        today = date.today()
        if formatted_date is not None:
            return formatted_date == today
        else:
            print("Error: Unable to parse date. Reloading...")
            return False
