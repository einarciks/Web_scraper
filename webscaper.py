import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field

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
class Apply_filters:
    def __init__(self, filters: Filters):
        self.filters = filters
    def apply(self, car):
        if self.filters.min_year and int(car.get("year", 0)) < self.filters.min_year:
            return False
        if self.filters.max_year and int(car.get("year", 0)) > self.filters.max_year:
            return False
        if self.filters.min_price and int(car.get("price", 0).replace("€", "").replace(",", "")) < self.filters.min_price:
            return False
        if self.filters.max_price and int(car.get("price", 0).replace("€", "").replace(",", "")) > self.filters.max_price:
            return False
        if self.filters.min_cap and float(car.get("engine", "0").replace("D", "").replace(",", ".")) < self.filters.min_cap:
            return False
        if self.filters.max_cap and float(car.get("engine", "0").replace("D", "").replace(",", ".")) > self.filters.max_cap:
            return False
        if self.filters.min_mileage and int(car.get("mileage", 0).replace("tūkst.", "000").replace(" ", "").replace(".", "")) < self.filters.min_mileage:
            return False
        if self.filters.max_mileage and int(car.get("mileage", 0).replace("tūkst.", "000").replace(" ", "").replace(".", "")) > self.filters.max_mileage:
            return False
        return True
    

def get_cars(marka, modelis, min_year, max_year, min_price, max_price, min_cap, max_cap, min_mileage, max_mileage):
    database = CarDatabase()

    base_url = f"https://www.ss.lv/lv/transport/cars/{marka}/{modelis}/sell/page{{}}.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    page = 1
    processed_ids = set()

    response = requests.get(base_url.format(1), headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')


    last_page = 1
    pagination = soup.find("div", class_="td2")
    if pagination:
        page_links = pagination.find_all("a")
        page_numbers = [int(a.text) for a in page_links if a.text.isdigit()]
        last_page = max(page_numbers) if page_numbers else 1

    print(f" Atrastas {last_page} lapas sludinājumu {marka.upper()} {modelis.upper()}!")


    while page <= last_page:
        url = base_url.format(page)
        print(f"Apstrādājam lapu {page}/{last_page}: {url}")

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Lapa nav pieejama!")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        ads = soup.find_all("tr", id=lambda x: x and x.startswith("tr_"))

        if not ads:  
            print("Nav vairāk sludinājumu")
            break

        for ad in ads:
            try:
                ad_id = ad["id"].split("_")[-1]
                if ad_id == "712":
                    continue
                elif ad_id in processed_ids:
                    print(f" Sludinājums {ad_id} jau apstrādāts, izlaižam.")
                    continue  
                processed_ids.add(ad_id)

                title_elem = ad.find("a", class_="am")
                title = title_elem.text.strip() + "..." if title_elem else "Nezināms"
                link = "https://www.ss.lv" + title_elem["href"] if title_elem else "Nav"

                td_elements = ad.find_all("td", class_=["msga2-o", "msga2-r"])
                year = td_elements[0].text.strip() if len(td_elements) > 0 else "Nav"
                engine = td_elements[1].text.strip() if len(td_elements) > 1 else "Nav"
                mileage = td_elements[2].text.strip().replace("tūkst.", "000") if len(td_elements) > 2 else "Nav"
                price = td_elements[3].text.strip() if len(td_elements) > 3 else "Nav"

                img_elem = ad.find("img", class_="isfoto")
                img_url = img_elem["src"] if img_elem else "Nav attēla"
                
                apply_filters = Apply_filters(Filters(min_year, max_year, min_price, max_price, min_cap, max_cap, min_mileage, max_mileage))
                if not apply_filters.apply({
                    "year": year,
                    "price": price,
                    "engine": engine,
                    "mileage": mileage
                }):
                    continue


                database.add({
                    "id": ad_id,
                    "title": title,
                    "year": year,
                    "engine": engine,
                    "mileage": mileage,
                    "price": price,
                    "link": link,
                    "image": img_url
                })

            except Exception as e:
                print(f" Kļūda apstrādājot sludinājumu: {e}")

        page += 1  
    
    return database
