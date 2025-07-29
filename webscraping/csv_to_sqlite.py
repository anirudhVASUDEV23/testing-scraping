import pandas as pd
import sqlite3
import os

def create_db_from_csv(csv_path, db_path, table_name):
    """
    Reads a CSV file and inserts its data into an SQLite database.
    If the table exists, it will be replaced.
    """
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}. Skipping database creation for {table_name}.")
        return

    # Ensure the directory for the database exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"Created database directory: {db_dir}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV file {csv_path}: {e}")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        # Using if_exists='replace' to ensure fresh data each time.
        # If you need to append and handle updates, you'll need more complex logic
        # (e.g., check for existing primary keys and update, or merge dataframes).
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Data from {csv_path} successfully written to {db_path} in table {table_name}")
    except sqlite3.Error as e:
        print(f"SQLite error during database operation for {table_name}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred for {table_name}: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Define paths relative to the project root (where the GitHub Action runs)
    BASE_WEB_SCRAPING_DIR = 'webscraping'
    APP_DIR = 'app'
    
    # Input CSV file paths
    main_product_csv = os.path.join(BASE_WEB_SCRAPING_DIR, 'flipkart_product_data.csv')
    unavailable_products_csv = os.path.join(BASE_WEB_SCRAPING_DIR, 'unavailable_products.csv')
    duplicate_products_csv = os.path.join(BASE_WEB_SCRAPING_DIR, 'duplicate_products.csv')

    # Output SQLite database path
    sqlite_db_path = os.path.join(APP_DIR, 'flipkart.db')

    print(f"Starting CSV to SQLite conversion. Database will be saved to: {sqlite_db_path}")

    # Convert main product data
    create_db_from_csv(main_product_csv, sqlite_db_path, 'flipkart_products')

    # Optionally, convert unavailable and duplicate products to separate tables
    # if you want them in the DB.
    # create_db_from_csv(unavailable_products_csv, sqlite_db_path, 'unavailable_products')
    # create_db_from_csv(duplicate_products_csv, sqlite_db_path, 'duplicate_products')

    print("CSV to SQLite conversion process completed.")