from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup
import lxml
import pandas as pd
import re
from datetime import datetime
from selenium.webdriver.common.keys import Keys
import os

# --- Configuration ---
search_box_text = 'sports shoes for women'
website_link = 'https://www.flipkart.com/'

OUTPUT_DIR = 'webscraping'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# --- Initiate Browser (with headless mode) ---
session_start_time = datetime.now().time()
print(f"Session Start Time: {session_start_time} ---------------------------> ")

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=chrome_options)
driver.get(website_link)
driver.maximize_window()

print('Waiting for search input...')
search_input = WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[autocomplete="off"]')))

print('Typing in search input...')
search_input.send_keys(search_box_text)

print('Submitting search form...')
search_input.send_keys(Keys.RETURN)

print('Waiting for search results...')
WebDriverWait(driver, 120).until( EC.presence_of_element_located((By.CSS_SELECTOR, '[target="_blank"]')) )

print('Collecting pagination links (only first page for quick testing)...')

all_pagination_links = []
try:
    current_url = driver.current_url
    if '&page=' in current_url:
        first_page_link = re.sub(r'&page=\d+', '&page=1', current_url)
    else:
        first_page_link = current_url + '&page=1'

    all_pagination_links.append(first_page_link)

    # --- CHANGE START ---
    # We are only interested in the first page for scraping 10 products
    # The loop for pages 2-25 is removed here.
    # --- CHANGE END ---

except Exception as e:
    print(f"Could not reliably collect first pagination link: {e}")
    # Fallback to initial approach if modification fails
    try:
        first_page_element = driver.find_elements(By.CSS_SELECTOR, 'nav a')[0]
        first_page_link = first_page_element.get_attribute('href')
        all_pagination_links = [first_page_link] # Only collect the first page's link
    except Exception as e_fallback:
        print(f"Fallback pagination link collection failed too: {e_fallback}")
        print("Please review pagination link collection logic based on Flipkart's current HTML.")
        driver.quit()
        exit()


print('Pagination Links Count:', len(all_pagination_links))
print("All Pagination Links: ", all_pagination_links)


print("Collecting Product Detail Page Links from selected pages")
all_product_links = []

for link in all_pagination_links: # This loop will now only run once for the first page
    driver.get(link)
    WebDriverWait(driver, 120).until(lambda d: d.execute_script('return document.readyState') == 'complete')

    try:
        WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.CLASS_NAME, 'rPDeLR')))
        all_products = driver.find_elements(By.CLASS_NAME, 'rPDeLR')
        all_links = [element.get_attribute('href') for element in all_products if element.get_attribute('href')]
        print(f"{link} Done ------> found {len(all_links)} products")
        all_product_links.extend(all_links)
    except Exception as e:
        print(f"No products found on {link} or elements not located: {e}")

print('All Product Detail Page Links Captured (from first page): ', len(all_product_links))

df_product_links = pd.DataFrame(all_product_links, columns=['product_links'])
df_product_links = df_product_links.drop_duplicates(subset=['product_links'])

print("Total Product Detail Page Links (after deduplication from first page)", len(df_product_links))

product_links_csv_path = os.path.join(OUTPUT_DIR, 'flipkart_product_links.csv')
df_product_links.to_csv(product_links_csv_path, index = False)
print(f"Product links saved to: {product_links_csv_path}")

driver.quit()
session_end_time = datetime.now().time()
print(f"Session End Time: {session_end_time} ---------------------------> ")

# --- Individual Product Detail Collection ---
session_start_time = datetime.now().time()
print(f"Session Start Time (Product Details): {session_start_time} ---------------------------> ")

df_product_links = pd.read_csv(product_links_csv_path)

# --- CHANGE START ---
# FOR DEMONSTRATION/TESTING: Remove this line to scrape all products from the collected links.
df_product_links = df_product_links.head(10)
# --- CHANGE END ---

all_product_links = df_product_links['product_links'].tolist()
print(f"Collecting Individual Product Detail Information for {len(all_product_links)} products (limited to 10)")

driver = webdriver.Chrome(options=chrome_options)

complete_product_details = []
unavailable_products = []
successful_parsed_urls_count = 0
complete_failed_urls_count = 0

for product_page_link in all_product_links:
    try:
        driver.get(product_page_link)

        WebDriverWait(driver, 60).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, 'VU-ZEz')))

        product_status_element = None
        try:
            product_status_element = driver.find_element(By.CLASS_NAME, 'Z8JjpR')
            product_status = product_status_element.text
            if 'unavailable' in product_status.lower() or 'sold out' in product_status.lower():
                unavailable_products.append(product_page_link)
                successful_parsed_urls_count += 1
                print(f"URL {successful_parsed_urls_count} completed (Unavailable) ---> {product_page_link}")
                continue
        except:
            pass

        brand = ''
        try:
            brand = driver.find_element(By.CLASS_NAME, 'mEh187').text
        except:
            print(f"Warning: Brand not found for {product_page_link}")

        title = ''
        try:
            title_element = driver.find_element(By.CLASS_NAME, 'VU-ZEz')
            title = title_element.text
            title = re.sub(r'\s*\([^)]*\)', '', title)
        except:
            print(f"Warning: Title not found for {product_page_link}")

        price = ''
        try:
            price_element = driver.find_element(By.CLASS_NAME, 'Nx9bqj')
            price = price_element.text
            price = re.findall(r'\d+', price)
            price = ''.join(price)
        except:
            print(f"Warning: Price not found for {product_page_link}")

        discount = ''
        try:
            discount_element = driver.find_element(By.CLASS_NAME, 'UkUFwK')
            discount = discount_element.text
            discount = re.findall(r'\d+', discount)
            discount = ''.join(discount)
            discount = float(discount) / 100
        except:
            pass

        avg_rating = ''
        total_ratings = ''
        try:
            product_review_status_element = driver.find_element(By.CLASS_NAME, 'E3XX7J')
            if 'be the first to review' in product_review_status_element.text.lower():
                avg_rating = ''
                total_ratings = ''
            else:
                avg_rating = driver.find_element(By.CLASS_NAME, 'XQDdHH').text
                total_ratings_text = driver.find_element(By.CLASS_NAME, 'Wphh3N').text.split(' ')[0]
                if ',' in total_ratings_text:
                    total_ratings = int(total_ratings_text.replace(',', ''))
                else:
                    total_ratings = int(total_ratings_text)
        except:
            pass

        successful_parsed_urls_count += 1
        print(f"URL {successful_parsed_urls_count} completed ******* {product_page_link}")
        complete_product_details.append([product_page_link, title, brand, price, discount, avg_rating, total_ratings])

    except Exception as e:
        print(f"Failed to parse product details for URL {product_page_link}: {e}")
        unavailable_products.append(product_page_link)
        complete_failed_urls_count += 1
        print(f"Failed URL Count {complete_failed_urls_count}")


df = pd.DataFrame(complete_product_details, columns=['product_link', 'title', 'brand', 'price', 'discount', 'avg_rating', 'total_ratings'])
df_duplicate_products = df[df.duplicated(subset=['brand', 'price', 'discount', 'avg_rating', 'total_ratings'], keep='first')]
df = df.drop_duplicates(subset=['brand', 'price', 'discount', 'avg_rating', 'total_ratings'], keep='first')
df_unavailable_products = pd.DataFrame(unavailable_products, columns=['link'])

print("Total product pages attempted: ", len(all_product_links))
print("Final Total Unique Products Scraped: ", len(df))
print("Total Unavailable Products Detected: ", len(df_unavailable_products))
print("Total Duplicate Products (content-wise): ", len(df_duplicate_products))

df.to_csv(os.path.join(OUTPUT_DIR, 'flipkart_product_data.csv'), index=False)
df_unavailable_products.to_csv(os.path.join(OUTPUT_DIR, 'unavailable_products.csv'), index=False)
df_duplicate_products.to_csv(os.path.join(OUTPUT_DIR, 'duplicate_products.csv'), index=False)

driver.quit()
session_end_time = datetime.now().time()
print(f"Session End Time (Product Details): {session_end_time} ---------------------------> ")