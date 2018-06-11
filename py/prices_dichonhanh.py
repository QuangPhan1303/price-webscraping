import sys
import os
import time
import datetime
import schedule
import re
import csv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# Parameters
SITE_NAME = "dichonhanh"
BASE_URL = "https://www.dichonhanh.vn"
PROJECT_PATH = re.sub("/py$", "", os.getcwd())
PATH_HTML = PROJECT_PATH + "/html/" + SITE_NAME + "/"
PATH_CSV = PROJECT_PATH + "/csv/" + SITE_NAME + "/"

# Selenium options
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
chrome_driver = PROJECT_PATH + "/bin/chromedriver"  # Chromedriver v2.38


def daily_task():
    """Main workhorse function. Support functions defined below"""
    global DATE
    DATE = str(datetime.date.today())
    # Initiate headless web browser
    browser = webdriver.Chrome(executable_path=chrome_driver,
                               chrome_options=options)
    # Download topsite and get categories directories
    base_file_name = "All_cat_" + DATE + ".html"
    fetch_html(BASE_URL, base_file_name, PATH_HTML, browser)
    html_file = open(PATH_HTML + base_file_name).read()
    categories = get_category_list(html_file)
    # Read each categories pages and scrape for data
    for cat in categories:
        cat_file = "cat_" + cat['name'] + "_" + DATE + ".html"
        download = fetch_html(cat['directlink'], cat_file, PATH_HTML, browser)
        if download:
            scrap_data(cat)
            next_page = find_next_page(cat)
            if next_page is not None and\
               next_page['directlink'] not in\
               [i['directlink'] for i in categories]:
                categories.append(next_page)
    # Compress data and html files
    compress_data()


def fetch_html(url, file_name, path, browser):
    """Fetch and download a html with provided path and file names"""
    if not os.path.exists(path):
        os.makedirs(path)
    if os.path.isfile(path + file_name) is False:
        attempts = 0
        while attempts < 5:
            try:
                browser.get(url)
                element = browser.find_element_by_xpath("/html")
                html_content = element.get_attribute("innerHTML")
                with open(path + file_name, "w") as f:
                    f.write(html_content)
                print("Downloaded ", file_name)
                return(True)
            except:
                attempts += 1
                print("Try again", file_name)
        else:
            print("Cannot download", file_name)
            return(False)
    else:
        print("Already downloaded ", file_name)
        return(True)


def get_category_list(top_html):
    """Get list of relative categories directories from the top page"""
    page_list = []
    toppage_soup = BeautifulSoup(top_html, "lxml")
    categories = toppage_soup.find('ul', {'class': 'menu-category'})
    categories = categories.findAll("li")
    categories_tag = [cat.findAll('a') for cat in categories]
    categories_tag = [item for sublist in categories_tag for item in sublist]
    for cat in categories_tag:
        page = {}
        link = re.sub(".+dichonhanh\.vn/", "", cat['href'])
        page['relativelink'] = link
        page['directlink'] = BASE_URL + link
        page['name'] = re.sub("/|\\?.=", "_", link)
        page['label'] = cat.get("title")
        page_list.append(page)
    # Remove duplicates
    page_list = [dict(t) for t in set(tuple(i.items()) for i in page_list)]
    return(page_list)


def scrap_data(cat):
    """Get item data from a category page and write to csv"""
    cat_file = open(PATH_HTML + "cat_" + cat['name'] + "_" +
                    DATE + ".html").read()
    cat_soup = BeautifulSoup(cat_file, "lxml")
    cat_div = cat_soup.find("div", {"class": "owl-carousel-item"})
    cat_div = cat_div.findAll("div", {"class": "i_block"}) if cat_div else None
    if cat_div is None:
        cat_div = []
    for item in cat_div:
        row = {}
        good_name = item.find('a')
        row['good_name'] = good_name.get('title') if good_name else None
        price = item.find('span', {"class": "price_feature"})
        row['price'] = price.contents[0] if price else None
        old_price = item.find('span', {"class": "price"})
        row['old_price'] = old_price.contents[0] if old_price else None
        row['id'] = good_name.get('href') if good_name else None
        row['category'] = cat['name']
        row['category_label'] = cat['label']
        row['date'] = DATE
        write_data(row)


def find_next_page(cat):
    """Find the next page button, return page data"""
    cat_file = open(PATH_HTML + "cat_" + cat['name'] + "_" +
                    DATE + ".html").read()
    cat_soup = BeautifulSoup(cat_file, "lxml")
    next_page = cat.copy()
    next_button = cat_soup.find("a", {"aria-label": "Next"})
    if next_button:
        link = re.sub(".+dichonhanh\.vn", "", cat['directlink'])
        link = re.sub("\?page=[0-9]+", "", link)
        link = link + next_button['href']
        next_page['relativelink'] = link
        next_page['directlink'] = BASE_URL + link
        next_page['name'] = re.sub("/|\\?.=", "_", link)
        return(next_page)
    else:
        return(None)


def write_data(item_data):
    """Write an item data as a row in csv. Create new file if needed"""
    fieldnames = ['good_name', 'price', 'old_price', 'id',
                  'category', 'category_label', 'date']
    file_exists = os.path.isfile(PATH_CSV + SITE_NAME + "_" + DATE + ".csv")
    if not os.path.exists(PATH_CSV):
        os.makedirs(PATH_CSV)
    with open(PATH_CSV + SITE_NAME + "_" + DATE + ".csv", "a") as f:
        writer = csv.DictWriter(f, fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(item_data)


def compress_data():
    """Compress downloaded .csv and .html files"""
    zip_csv = "cd " + PATH_CSV + "&& tar -cvzf " + SITE_NAME + "_" + \
        DATE + ".tar.gz *" + SITE_NAME + "_" + DATE + "* --remove-files"
    zip_html = "cd " + PATH_HTML + "&& tar -cvzf " + SITE_NAME + "_" + \
        DATE + ".tar.gz *" + DATE + ".html* --remove-files"
    os.system(zip_csv)
    os.system(zip_html)


if "test" in sys.argv:
    daily_task()
else:
    schedule.every().day.at("06:00").do(daily_task)
    while True:
        schedule.run_pending()
        time.sleep(1)
