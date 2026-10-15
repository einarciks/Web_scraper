import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

MAX_WORKERS = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


@dataclass
class CarDatabase:
    cars: list = field(default_factory=list)
    seen_ids: set = field(default_factory=set)
    is_complete: bool = True
    def add(self, data):
        self.cars.append(data)
    def __iter__(self):
        return iter(self.cars)
    def __len__(self):
        return len(self.cars)


def create_session():
    """One shared session reuses TCP/TLS connections to ss.lv across threads."""
    session = requests.Session()
    session.headers.update(HEADERS)
    adapter = requests.adapters.HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
    session.mount("https://", adapter)
    return session


def scrape_ad_details(link, session):
    try:
        response = session.get(link, timeout=10)
        if response.status_code != 200:
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}

        field_map = {
            "tdo_18": "year",
            "tdo_15": "engine",
            "tdo_16": "mileage",
            "tdo_17": "color",
            "tdo_32": "body_type",
            "tdo_35": "gearbox",
            "tdo_223": "inspection",
            "tdo_8":  "price",
        }

        for td_id, field_name in field_map.items():
            elem = soup.find("td", id=td_id)
            if elem:
                details[field_name] = elem.text.strip()

        images = []
        photo_divs = soup.find_all("div", class_="pic_dv_thumbnail")
        for div in photo_divs:
            photo_link = div.find("a", href=True)
            img = div.find("img", class_="pic_thumbnail")
            # SS.lv exposes an .800.jpg version through the gallery link and a
            # low-resolution .t.jpg thumbnail through the image source.
            if photo_link:
                images.append(photo_link["href"])
            elif img and img.get("src"):
                images.append(img["src"])
        
        details["images"] = images

        return details

    except Exception as e:
        print(f"Kļūda: {e}")
        return {}


def process_single_ad(ad, session):
    """Apstrādā vienu sludinājumu — paredzēts paralēlai izpildei"""
    try:
        ad_id = ad["id"].split("_")[-1]
        if ad_id == "712":
            return None

        title_elem = ad.find("a", class_="am")
        title = title_elem.text.strip() if title_elem else "Nezināms"
        link = "https://www.ss.lv" + title_elem["href"] if title_elem else None
        if not link:
            return None

        td_elements = ad.find_all("td", class_=["msga2-o", "msga2-r"])
        year_fallback    = td_elements[0].text.strip() if len(td_elements) > 0 else "Nav"
        engine_fallback  = td_elements[1].text.strip() if len(td_elements) > 1 else "Nav"
        mileage_fallback = td_elements[2].text.strip() if len(td_elements) > 2 else "Nav"
        price_fallback   = td_elements[3].text.strip() if len(td_elements) > 3 else "Nav"

        img_elem = ad.find("img", class_="isfoto")
        img_url = img_elem["src"] if img_elem else "Nav attēla"

        details = scrape_ad_details(link, session)

        year    = details.get("year",    year_fallback)
        engine  = details.get("engine",  engine_fallback)
        mileage = details.get("mileage", mileage_fallback)
        price   = details.get("price",   price_fallback)
        color   = details.get("color", "Nav").strip()
        body_type = details.get("body_type", "Nav")
        gearbox = details.get("gearbox", "Nav")
        inspection = details.get("inspection", "Nav")

        return {
            "id":         ad_id,
            "title":      title,
            "year":       year,
            "engine":     engine,
            "mileage":    mileage,
            "price":      price,
            "link":       link,
            "image":      img_url,
            "color":      color,
            "body_type":  body_type,
            "gearbox":    gearbox,
            "inspection": inspection,
            "image":  details.get("images", [img_url])[0] if details.get("images") else img_url,
            "images": details.get("images", [img_url]),
        }

    except Exception as e:
        print(f"Kļūda apstrādājot sludinājumu: {e}")
        return None


def find_ads(soup):
    return soup.find_all("tr", id=lambda x: x and x.startswith("tr_"))


def fetch_list_page(session, url, page):
    """Ielādē vienu saraksta lapu; atgriež sludinājumu rindas vai None kļūdas gadījumā."""
    try:
        response = session.get(url, timeout=10)
    except requests.RequestException as error:
        print(f"Kļūda ielādējot lapu {page}: {error}")
        return None
    if response.status_code != 200:
        print(f"Kļūda ielādējot lapu {page}: HTTP {response.status_code}")
        return None
    # SS.lv redirects pages that no longer exist back to page 1.
    if not response.url.endswith(f"page{page}.html"):
        return None
    return find_ads(BeautifulSoup(response.text, 'html.parser'))


def get_cars(marka, modelis, progress=None):
    """progress(stage, done, total) tiek izsaukts ar stage "pages" vai "ads"."""
    database = CarDatabase()
    report = progress or (lambda stage, done, total: None)

    base_url = f"https://www.ss.lv/en/transport/cars/{marka}/{modelis}/sell/page{{}}.html"
    session = create_session()

    try:
        response = session.get(base_url.format(1), timeout=10)
    except requests.RequestException as error:
        print(f"Kļūda ielādējot SS.lv sarakstu: {error}")
        database.is_complete = False
        return database
    if response.status_code != 200:
        print(f"Kļūda ielādējot SS.lv sarakstu: HTTP {response.status_code}")
        database.is_complete = False
        return database
    soup = BeautifulSoup(response.text, 'html.parser')

    last_page = 1
    pagination = soup.find("div", class_="td2")
    if pagination:
        # SS.lv shows only a window of page numbers, but on page 1 the
        # "Previous" link points to the last page, so read numbers from hrefs.
        page_numbers = [
            int(match.group(1))
            for a in pagination.find_all("a", href=True)
            if (match := re.search(r"page(\d+)\.html", a["href"]))
        ]
        last_page = max(page_numbers) if page_numbers else 1

    print(f"Atrastas {last_page} lapas — {marka.upper()} {modelis.upper()}")

    # 1. solis — savācam visus sludinājumus no visām lapām (1. lapa jau ielādēta)
    ads_by_page = {1: find_ads(soup)}
    report("pages", 1, last_page)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_list_page, session, base_url.format(page), page): page
            for page in range(2, last_page + 1)
        }
        for done, future in enumerate(as_completed(futures), start=2):
            ads_by_page[futures[future]] = future.result()
            report("pages", done, last_page)

    processed_ids = set()
    all_ads = []
    for page in range(1, last_page + 1):
        ads = ads_by_page[page]
        if not ads:
            # Kļūda vai tukša lapa pirms pēdējās — saraksts nav pilnīgs.
            if ads is None or page < last_page:
                database.is_complete = False
            continue
        for ad in ads:
            ad_id = ad["id"].split("_")[-1]
            if ad_id not in processed_ids and ad_id != "712":
                processed_ids.add(ad_id)
                database.seen_ids.add(ad_id)
                all_ads.append(ad)

    print(f"Kopā {len(all_ads)} sludinājumi — sākam paralēlo apstrādi...")

    # 2. solis — paralēli atverams katru sludinājumu
    report("ads", 0, len(all_ads))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_single_ad, ad, session): ad
            for ad in all_ads
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result:
                database.add(result)
            report("ads", completed, len(all_ads))
            if completed % 10 == 0:
                print(f"  Apstrādāti {completed}/{len(all_ads)}...")

    session.close()
    print(f"Pabeigts! Atrasti {len(database)} sludinājumi.")
    return database
