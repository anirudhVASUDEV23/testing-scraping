from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options # Import Options
import time
from bs4 import BeautifulSoup
import lxml
import pandas as pd
import re
from datetime import datetime
from selenium.webdriver.common.keys import Keys
import os # Import os for path manipulation

# --- Configuration ---
search_box_text = 'sports shoes for women'
website_link = 'https://www.flipkart.com/'

# Define output directory for CSVs (relative to script's execution context)
# When run by GitHub Actions, the working directory is 'your_project_root/'
# So, CSVs should go into 'webscraping/'
OUTPUT_DIR = 'webscraping'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# --- Initiate Browser (with headless mode) ---
session_start_time = datetime.now().time()
print(f"Session Start Time: {session_start_time} ---------------------------> ")

chrome_options = Options()
chrome_options.add_argument("--headless")           # Run Chrome in headless mode (no UI)
chrome_options.add_argument("--no-sandbox")         # Bypass OS security model, required for some environments
chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
chrome_options.add_argument("--window-size=1920,1080") # Set a window size for consistent rendering

driver = webdriver.Chrome(options=chrome_options)
driver.get(website_link)
driver.maximize_window() # Maximize even in headless mode can sometimes help with element visibility

print('Waiting for search input...')
search_input = WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[autocomplete="off"]')))

print('Typing in search input...')
search_input.send_keys(search_box_text)

print('Submitting search form...')
search_input.send_keys(Keys.RETURN)

print('Waiting for search results...')
WebDriverWait(driver, 120).until( EC.presence_of_element_located((By.CSS_SELECTOR, '[target="_blank"]')) )

print('Collecting pagination links...')

# We want first 25 pages [pagination link] [1000 Products]
all_pagination_links =[]

# Get the first page link
# It's safer to find all 'a' tags within the pagination nav and select the one for page 1
# This might need adjustment based on Flipkart's exact HTML structure if 'nav a' isn't precise enough
# Let's try to get the current URL and assume it's page 1, then modify it
current_url = driver.current_url
# Example: if current_url is 'https://www.flipkart.com/search?q=sports+shoes+for+women&page=1'
# we want to modify the 'page=1' part.
# This assumes the URL structure consistently contains '&page=' or similar.
# A more robust way might be to find the 'Next' button or specific page number links.

# For robust pagination, let's try finding the "Next" button or page numbers
try:
    # Find the element for page 1 to extract its base link
    # This might need to be more specific, e.g., 'nav div a' or 'nav span a' depending on current HTML
    # Let's try to infer from the current URL after search
    base_url = driver.current_url
    if '&page=' in base_url:
        first_page_link = re.sub(r'&page=\d+', '&page=1', base_url)
    else:
        # If no page parameter, assume it's the first page and append it
        first_page_link = base_url + '&page=1'
    
    all_pagination_links.append(first_page_link)

    for i in range(2, 26): # For pages 2 to 25
        new_pagination_link = re.sub(r'&page=\d+', f'&page={i}', first_page_link)
        all_pagination_links.append(new_pagination_link)
        
except Exception as e:
    print(f"Could not reliably collect pagination links using direct modification, falling back to initial approach if needed: {e}")
    # Fallback/alternative if the above fails, or simplify to initial approach from your script:
    # This assumes 'nav a' consistently returns pagination links.
    try:
        first_page_element = driver.find_elements(By.CSS_SELECTOR, 'nav a')[0]
        first_page_link = first_page_element.get_attribute('href')
        all_pagination_links = [first_page_link] # Start with first page link
        for i in range(2, 26):
            new_pagination_link = first_page_link[: -1] + str(i) # Assuming last char is page number
            all_pagination_links.append(new_pagination_link)
    except Exception as e_fallback:
        print(f"Fallback pagination link collection failed too: {e_fallback}")
        print("Please review pagination link collection logic based on Flipkart's current HTML.")
        # Exit or handle gracefully if no pagination links are found
        driver.quit()
        exit()


print('Pagination Links Count:', len(all_pagination_links))
print("All Pagination Links: ", all_pagination_links)


print("Collecting Product Detail Page Links")
all_product_links = []

for link in all_pagination_links:
    driver.get(link)
    WebDriverWait(driver, 120).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    
    # Wait until product elements are located
    try:
        WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.CLASS_NAME, 'rPDeLR')))
        all_products = driver.find_elements(By.CLASS_NAME, 'rPDeLR')
        all_links = [element.get_attribute('href') for element in all_products if element.get_attribute('href')] # Ensure href is not None
        print(f"{link} Done ------> found {len(all_links)} products")
        all_product_links.extend(all_links)
    except Exception as e:
        print(f"No products found on {link} or elements not located: {e}")

print('All Product Detail Page Links Captured: ', len(all_product_links))

# Creating a DataFrame from the list
df_product_links = pd.DataFrame(all_product_links, columns=['product_links'])
# remove any duplicates
df_product_links = df_product_links.drop_duplicates(subset=['product_links'])

print("Total Product Detail Page Links (after deduplication)", len(df_product_links))

# Save to CSV in the OUTPUT_DIR
product_links_csv_path = os.path.join(OUTPUT_DIR, 'flipkart_product_links.csv')
df_product_links.to_csv(product_links_csv_path, index = False)
print(f"Product links saved to: {product_links_csv_path}")

driver.quit() # Use quit() to close the browser and end the session
session_end_time = datetime.now().time()
print(f"Session End Time: {session_end_time} ---------------------------> ")

# --- Individual Product Detail Collection ---
session_start_time = datetime.now().time()
print(f"Session Start Time (Product Details): {session_start_time} ---------------------------> ")

# reading the csv file which contain all product links from the OUTPUT_DIR
df_product_links = pd.read_csv(product_links_csv_path)

# Remove the below line to scrap all the products. For demonstration purpose we are scraping only 10 products
# df_product_links = df_product_links.head(10)

all_product_links = df_product_links['product_links'].tolist()
print(f"Collecting Individual Product Detail Information for {len(all_product_links)} products")

driver = webdriver.Chrome(options=chrome_options) # Restart driver for product details

complete_product_details = []
unavailable_products = []
successful_parsed_urls_count = 0
complete_failed_urls_count = 0

for product_page_link in all_product_links:
    try:
        driver.get(product_page_link)

        WebDriverWait(driver, 60).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        
        # Explicitly wait for a common element indicating page content is loaded
        # For product pages, a good indicator might be the title or price element
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, 'VU-ZEz'))) # Product Title

        # Checking if product is available or not
        product_status_element = None
        try:
            product_status_element = driver.find_element(By.CLASS_NAME, 'Z8JjpR') # This class indicates availability
            product_status = product_status_element.text
            if 'unavailable' in product_status.lower() or 'sold out' in product_status.lower():
                unavailable_products.append(product_page_link)
                successful_parsed_urls_count += 1
                print(f"URL {successful_parsed_urls_count} completed (Unavailable) ---> {product_page_link}")
                continue # Skip to next product if unavailable
        except:
            # If the element is not found, assume product is available
            pass

        # Brand
        brand = ''
        try:
            brand = driver.find_element(By.CLASS_NAME, 'mEh187').text
        except:
            print(f"Warning: Brand not found for {product_page_link}")

        # Title
        title = ''
        try:
            title_element = driver.find_element(By.CLASS_NAME, 'VU-ZEz')
            title = title_element.text
            title = re.sub(r'\s*\([^)]*\)', '', title)  # removing data within parenthesis (color information)
        except:
            print(f"Warning: Title not found for {product_page_link}")

        # Price
        price = ''
        try:
            price_element = driver.find_element(By.CLASS_NAME, 'Nx9bqj')
            price = price_element.text
            price = re.findall(r'\d+', price)
            price = ''.join(price)
        except:
            print(f"Warning: Price not found for {product_page_link}")

        # Discount
        discount = ''
        try:
            discount_element = driver.find_element(By.CLASS_NAME, 'UkUFwK')
            discount = discount_element.text
            discount = re.findall(r'\d+', discount)
            discount = ''.join(discount)
            discount = float(discount) / 100 # Convert to float for percentage
        except:
            pass # No discount, or element not found

        # Ratings
        avg_rating = ''
        total_ratings = ''
        try:
            # Check for "Be the first to Review" status
            product_review_status_element = driver.find_element(By.CLASS_NAME, 'E3XX7J')
            if 'be the first to review' in product_review_status_element.text.lower():
                avg_rating = ''
                total_ratings = ''
            else:
                # Assuming ratings elements are present if not "first to review"
                avg_rating = driver.find_element(By.CLASS_NAME, 'XQDdHH').text
                total_ratings_text = driver.find_element(By.CLASS_NAME, 'Wphh3N').text.split(' ')[0]
                # Remove commas from total_ratings
                if ',' in total_ratings_text:
                    total_ratings = int(total_ratings_text.replace(',', ''))
                else:
                    total_ratings = int(total_ratings_text)
        except:
            pass # No ratings or review status element found

        successful_parsed_urls_count += 1
        print(f"URL {successful_parsed_urls_count} completed ******* {product_page_link}")
        complete_product_details.append([product_page_link, title, brand, price, discount, avg_rating, total_ratings])

    except Exception as e:
        print(f"Failed to parse product details for URL {product_page_link}: {e}")
        unavailable_products.append(product_page_link)
        complete_failed_urls_count += 1
        print(f"Failed URL Count {complete_failed_urls_count}")


# Create pandas dataframe
df = pd.DataFrame(complete_product_details, columns=['product_link', 'title', 'brand', 'price', 'discount', 'avg_rating', 'total_ratings'])

# Duplicates processing based on content (not just link)
df_duplicate_products = df[df.duplicated(subset=['brand', 'price', 'discount', 'avg_rating', 'total_ratings'], keep='first')]
df = df.drop_duplicates(subset=['brand', 'price', 'discount', 'avg_rating', 'total_ratings'], keep='first')

# Unavailable products
df_unavailable_products = pd.DataFrame(unavailable_products, columns=['link'])


# Printing the stats
print("Total product pages attempted: ", len(all_product_links))
print("Final Total Unique Products Scraped: ", len(df))
print("Total Unavailable Products Detected: ", len(df_unavailable_products))
print("Total Duplicate Products (content-wise): ", len(df_duplicate_products))


# Saving all the files in the OUTPUT_DIR
df.to_csv(os.path.join(OUTPUT_DIR, 'flipkart_product_data.csv'), index=False)
df_unavailable_products.to_csv(os.path.join(OUTPUT_DIR, 'unavailable_products.csv'), index=False)
df_duplicate_products.to_csv(os.path.join(OUTPUT_DIR, 'duplicate_products.csv'), index=False)

driver.quit()
session_end_time = datetime.now().time()
print(f"Session End Time (Product Details): {session_end_time} ---------------------------> ")