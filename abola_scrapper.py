import requests
from bs4 import BeautifulSoup
import json
import time
import logging
import os
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException

# Logging
logging.basicConfig(filename='scraping.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def download_image(url, folder="images"):
    if not url or not url.startswith("http"):
        return None

    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = os.path.join(folder, os.path.basename(url))
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        return filename
    return None

def is_valid_news_link(link):
    pattern = re.compile(r"https://www\\.abola\\.pt/.+/noticias/.+-\\d+")
    return bool(pattern.match(link))

def scrape_abola():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except WebDriverException as e:
        print("Erro ao iniciar Chrome:", e)
        return

    url = "https://www.abola.pt/"
    driver.get(url)
    time.sleep(6)  # Mais tempo para carregar o conteúdo dinâmico

    page_source = driver.page_source
    driver.quit()

    # DEBUG: salvar o HTML carregado para inspecionar
    with open("debug_abola.html", "w", encoding="utf-8") as f:
        f.write(page_source)

    soup = BeautifulSoup(page_source, 'html.parser')
    articles = []

    article_blocks = soup.select("article")
    print(f"Artigos encontrados: {len(article_blocks)}")

    for item in article_blocks:
        link_element = item.find("a", href=True)
        if not link_element:
            continue

        raw_link = link_element['href']
        link = f"https://www.abola.pt{raw_link}" if raw_link.startswith("/") else raw_link

        if not is_valid_news_link(link):
            continue

        image_element = item.find("img")
        image_url = image_element.get("data-src") or image_element.get("src") if image_element else None
        image_path = download_image(image_url) if image_url else None

        title = "Sem título"
        article_text = "Sem conteúdo"

        try:
            response = requests.get(link)
            article_soup = BeautifulSoup(response.text, 'html.parser')

            title_element = article_soup.find("h1", class_="titulo")
            title = title_element.text.strip() if title_element else "Sem título"

            content_elements = article_soup.find_all("p")
            article_text = " ".join([p.text.strip() for p in content_elements if p.text.strip()])
        except Exception as e:
            logging.error(f"Erro ao extrair conteúdo da notícia {link}: {e}")

        articles.append({
            "title": title,
            "link": link,
            "image": image_path,
            "content": article_text
        })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"abola_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

    print(f"{len(articles)} artigos guardados em {filename}")
    logging.info(f"Dados guardados em {filename}")

if __name__ == "__main__":
    scrape_abola()
