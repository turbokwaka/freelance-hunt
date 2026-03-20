from .load_django import *
from parser_app.models import Ad
from telegram_notify import send_ad_notification

from curl_cffi import requests
from bs4 import BeautifulSoup
import time

ADS_URL = "https://freelancehunt.com/projects?skills%5B%5D=169&skills%5B%5D=170"


def get_project_details(url, headers):
    try:
        # Додаємо impersonate="chrome120", щоб імітувати реальний браузер
        response = requests.get(url, headers=headers, impersonate="chrome120")
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.select_one('div.h1-container h1')
        title = title_tag.text.strip() if title_tag else "Не знайдено"

        budget_tag = soup.select_one('div.h1-container span.price')
        budget = budget_tag.text.strip() if budget_tag else "Договірний / Не вказано"

        categories_tags = soup.select('div.categories-container a')
        categories = ", ".join([cat.text.strip() for cat in categories_tags]) if categories_tags else ""

        employer_tag = soup.select_one('span[data-freelancehunt-selector="author"] a.profile-name')
        employer = employer_tag.text.strip() if employer_tag else "Не знайдено"

        desc_tag = soup.select_one('span[data-freelancehunt-selector="description"]')
        description = desc_tag.text.strip().replace('\n', ' ') if desc_tag else "Не знайдено"
        short_description = (description[:200] + '...') if len(description) > 200 else description

        return {
            "title": title,
            "budget": budget,
            "employer": employer,
            "categories": categories,
            "description": short_description,
            "url": url
        }

    except Exception as e:
        print(f"Помилка при завантаженні {url}: {e}")
        return None


def run_parser():
    cookie_string = "cookieyes-consent=consentid:U0pYR3owbVB5ZGlxMG4xTWJ2NTBHMGdkcFNHZ0tTRVY,consent:yes,action:no,necessary:yes,functional:yes,analytics:yes,performance:yes,advertisement:yes,other:yes; _gcl_au=1.1.1376940466.1772702324; _ga=GA1.1.2079057660.1772702324; _ga_D5VKDWKRBW=GS2.1.s1773255203$o2$g1$t1773255203$j60$l0$h1255506203$ddd14vSLhmD5D-GHdaarYuX6OEG9HuJufsw; _fbp=fb.1.1773255204259.647839639539222162; _clck=1vbeyty%5E2%5Eg49%5E0%5E2255; _clsk=8s6s39%5E1773255205397%5E1%5E1%5Ev.clarity.ms%2Fcollect"

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "uk,en-US;q=0.9,en;q=0.8",
        "Cookie": cookie_string,
        "Referer": "https://freelancehunt.com/",
    }

    # Отримуємо множину вже збережених URL
    existing_urls = set(Ad.objects.values_list("url", flat=True))

    try:
        print("Завантаження списку проєктів...")
        response = requests.get(ADS_URL, headers=headers, impersonate="chrome120")
        soup = BeautifulSoup(response.text, 'html.parser')

        project_links = soup.select('table.project-list td.left a.visitable')

        if not project_links:
            print("Оголошень не знайдено. Перевіряємо, що повернув сайт...")
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print(
                "HTML сторінки збережено у файл 'debug.html'. Відкрий його в браузері, щоб перевірити, чи це капча/Cloudflare.")
            return

        print(f"Знайдено проєктів: {len(project_links)}. Починаю збір деталей...\n")
        print("-" * 60)

        for index, link in enumerate(project_links[:5], start=1):
            project_url = link['href']
            if project_url.startswith('/'):
                project_url = "https://freelancehunt.com" + project_url

            if project_url in existing_urls:
                print(f"[{index}] Пропускаю (вже збережено): {project_url}")
                continue

            print(f"[{index}] Парсинг: {project_url}")
            details = get_project_details(project_url, headers)

            if details:
                print(f"📌 Назва: {details['title']}")
                print(f"💰 Бюджет: {details['budget']}")
                print(f"📂 Категорії: {details['categories']}")
                print(f"📝 Опис: {details['description']}")

                ad, created = Ad.objects.update_or_create(
                    url=details['url'],
                    defaults={
                        "title": details['title'],
                        "budget": details['budget'],
                        "employer": details['employer'],
                        "categories": details['categories'],
                        "description": details['description']
                    }
                )

                if created:
                    print(f"📨 Надсилаю в Telegram...")
                    try:
                        send_ad_notification(ad.id, details)
                        print(f"✅ Повідомлення надіслано!")
                    except Exception as e:
                        print(f"⚠️ Помилка надсилання в Telegram: {e}")

            print("-" * 60)
            time.sleep(2)

        print("Парсинг завершено!")

    except Exception as e:
        print(f"Помилка при отриманні списку проєктів: {e}")


if __name__ == "__main__":
    run_parser()