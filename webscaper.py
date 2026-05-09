import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
@dataclass
class CarDatabase:
    cars: list = field(default_factory=list)
    def add(self, data):
        self.cars.append(data)
    def __iter__(self):
        return iter(self.cars)
    def __len__(self):
        return len(self.cars)
@dataclass
class Filters:
    min_year: int = None
    max_year: int = None
    min_price: int = None
    max_price: int = None
    min_cap: float = None
    max_cap: float = None
    min_mileage: int = None
    max_mileage: int = None
    Gearbox: str = None
    Body_type: str = None
    Color: str = None
class Apply_filters:
    def __init__(self, filters: Filters):
        self.filters = filters
    def apply(self, car):
        if self.filters.min_year and int(car.get("year", 0).split()[0]) < self.filters.min_year:
            return False
        if self.filters.max_year and int(car.get("year", 0).split()[0]) > self.filters.max_year:
            return False
        if self.filters.min_price and int(car.get("price", 0).split()[0].replace("€", "").replace(",", "")) < self.filters.min_price:
            return False
        if self.filters.max_price and int(car.get("price", 0).split()[0].replace("€", "").replace(",", "")) > self.filters.max_price:
            return False
        if self.filters.min_cap and float(car.get("engine", "0").split()[0].replace("D", "").replace(",", ".")) < self.filters.min_cap:
            return False
        if self.filters.max_cap and float(car.get("engine", "0").split()[0].replace("D", "").replace(",", ".")) > self.filters.max_cap:
            return False
        if self.filters.min_mileage and int(car.get("mileage", 0).replace(" ", "").replace("-", "")) < self.filters.min_mileage:
            return False
        if self.filters.max_mileage and int(car.get("mileage", 0).replace(" ", "").replace("-", "")) > self.filters.max_mileage:
            return False
        if self.filters.Gearbox:
            car_gearbox = car.get("gearbox", "Nav").split()[0]
            if car_gearbox not in self.filters.Gearbox:
                return False
        if self.filters.Body_type:
            car_body = car.get("body_type", "Nav")
            if car_body not in self.filters.Body_type:
                return False
        if self.filters.Color:
            car_color = car.get("color", "Nav")
            if car_color not in self.filters.Color:
                return False
        return True
    

def scrape_ad_details(link, headers):
    try:
        response = requests.get(link, headers=headers, timeout=10)
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
            img = div.find("img", class_="pic_thumbnail")
            if img and img.get("src"):
                images.append(img["src"])
        
        details["images"] = images

        return details

    except Exception as e:
        print(f"Kļūda: {e}")
        return {}


def process_single_ad(ad, headers, filters_obj):
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

        details = scrape_ad_details(link, headers)

        year    = details.get("year",    year_fallback)
        engine  = details.get("engine",  engine_fallback)
        mileage = details.get("mileage", mileage_fallback)
        price   = details.get("price",   price_fallback)
        color   = details.get("color",   "Nav").split()[0]
        body_type = details.get("body_type", "Nav")
        gearbox = details.get("gearbox", "Nav")
        inspection = details.get("inspection", "Nav")

        if not filters_obj.apply({"year": year, "price": price, "engine": engine, "mileage": mileage, "color": color, "body_type": body_type, "gearbox": gearbox}):
            return None

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


def get_cars(marka, modelis, min_year, max_year, min_price, max_price, min_cap, max_cap, min_mileage, max_mileage, gearbox, body_type, color):
    database = CarDatabase()
    filters_obj = Apply_filters(Filters(min_year, max_year, min_price, max_price, min_cap, max_cap, min_mileage, max_mileage, gearbox, body_type, color))

    base_url = f"https://www.ss.lv/en/transport/cars/{marka}/{modelis}/sell/page{{}}.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(base_url.format(1), headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    last_page = 1
    pagination = soup.find("div", class_="td2")
    if pagination:
        page_links = pagination.find_all("a")
        page_numbers = [int(a.text) for a in page_links if a.text.isdigit()]
        last_page = max(page_numbers) if page_numbers else 1

    print(f"Atrastas {last_page} lapas — {marka.upper()} {modelis.upper()}")

    processed_ids = set()
    all_ads = []

    # 1. solis — savācam visus sludinājumus no visām lapām
    for page in range(1, last_page + 1):
        url = base_url.format(page)
        print(f"Lapa {page}/{last_page}: {url}")

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        ads = soup.find_all("tr", id=lambda x: x and x.startswith("tr_"))
        if not ads:
            break

        for ad in ads:
            ad_id = ad["id"].split("_")[-1]
            if ad_id not in processed_ids and ad_id != "712":
                processed_ids.add(ad_id)
                all_ads.append(ad)

    print(f"Kopā {len(all_ads)} sludinājumi — sākam paralēlo apstrādi...")

    # 2. solis — paralēli atverams katru sludinājumu
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(process_single_ad, ad, headers, filters_obj): ad
            for ad in all_ads
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result:
                database.add(result)
            if completed % 10 == 0:
                print(f"  Apstrādāti {completed}/{len(all_ads)}...")

    print(f"Pabeigts! Atrasti {len(database)} sludinājumi.")
    return database

