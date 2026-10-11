"""SQLite storage and query helpers for scraped SS.lv advertisements."""

import json
import re
import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).with_name("cars.sqlite3")


def _number(value, decimal=False):
    """Extract the first number from a value displayed by SS.lv."""
    if value is None:
        return None
    text = str(value).replace("\u00a0", " ").replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text.replace(" ", ""))
    if not match:
        return None
    return float(match.group()) if decimal else int(float(match.group()))


class CarRepository:
    def __init__(self, path=DATABASE_PATH):
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _create_schema(self):
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cars (
                listing_id TEXT PRIMARY KEY,
                make TEXT NOT NULL, model TEXT NOT NULL, title TEXT,
                year_text TEXT, year INTEGER, engine_text TEXT, engine_capacity REAL,
                mileage_text TEXT, mileage INTEGER, price_text TEXT, price INTEGER,
                link TEXT NOT NULL, image TEXT, images_json TEXT NOT NULL DEFAULT '[]',
                color TEXT, body_type TEXT, gearbox TEXT, inspection TEXT,
                scraped_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_cars_search
                ON cars(make, model, year, price, engine_capacity, mileage);
            """
        )
        self.connection.commit()

    def save_cars(self, cars, make, model):
        """Insert new advertisements or refresh ones already in the database."""
        rows = [(
            str(car["id"]), make.lower(), model.lower(), car.get("title"),
            car.get("year"), _number(car.get("year")),
            car.get("engine"), _number(car.get("engine"), decimal=True),
            car.get("mileage"), _number(car.get("mileage")),
            car.get("price"), _number(car.get("price")), car.get("link"),
            car.get("image"), json.dumps(car.get("images", [])), car.get("color"),
            car.get("body_type"), car.get("gearbox"), car.get("inspection"),
        ) for car in cars]
        self.connection.executemany(
            """
            INSERT INTO cars (
                listing_id, make, model, title, year_text, year, engine_text,
                engine_capacity, mileage_text, mileage, price_text, price, link,
                image, images_json, color, body_type, gearbox, inspection
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(listing_id) DO UPDATE SET
                make=excluded.make, model=excluded.model, title=excluded.title,
                year_text=excluded.year_text, year=excluded.year,
                engine_text=excluded.engine_text, engine_capacity=excluded.engine_capacity,
                mileage_text=excluded.mileage_text, mileage=excluded.mileage,
                price_text=excluded.price_text, price=excluded.price, link=excluded.link,
                image=excluded.image, images_json=excluded.images_json, color=excluded.color,
                body_type=excluded.body_type, gearbox=excluded.gearbox,
                inspection=excluded.inspection, scraped_at=CURRENT_TIMESTAMP
            """, rows,
        )
        self.connection.commit()
        return len(rows)

    def remove_missing_cars(self, make, model, active_ids):
        """Remove cars absent from a complete SS.lv result set for one make/model."""
        parameters = [make.lower(), model.lower()]
        query = "DELETE FROM cars WHERE make = ? AND model = ?"
        if active_ids:
            placeholders = ",".join("?" for _ in active_ids)
            query += f" AND listing_id NOT IN ({placeholders})"
            parameters.extend(str(listing_id) for listing_id in active_ids)
        cursor = self.connection.execute(query, parameters)
        self.connection.commit()
        return cursor.rowcount

    def search(self, make=None, model=None, min_year=None, max_year=None,
               min_price=None, max_price=None, min_cap=None, max_cap=None,
               min_mileage=None, max_mileage=None, gearbox=None, body_type=None,
               color=None):
        """Return cars using only SQL filters and bound parameters."""
        where, params = [], []

        def range_filter(column, minimum, maximum):
            if minimum is not None:
                where.append(f"{column} >= ?")
                params.append(minimum)
            if maximum is not None:
                where.append(f"{column} <= ?")
                params.append(maximum)

        if make:
            where.append("make = ?")
            params.append(make.lower())
        if model:
            where.append("model LIKE ?")
            params.append(f"%{model.lower()}%")
        range_filter("year", min_year, max_year)
        range_filter("price", min_price, max_price)
        range_filter("engine_capacity", min_cap, max_cap)
        range_filter("mileage", min_mileage, max_mileage)
        for column, values in (("gearbox", gearbox), ("body_type", body_type)):
            if values:
                where.append(f"{column} IN ({','.join('?' for _ in values)})")
                params.extend(values)
        if color:
            where.append("(" + " OR ".join("color LIKE ? COLLATE NOCASE" for _ in color) + ")")
            params.extend(f"{value}%" for value in color)

        query = "SELECT * FROM cars"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY scraped_at DESC, price ASC"
        result = self.connection.execute(query, params).fetchall()
        cars = []
        for row in result:
            car = dict(row)
            car.update({
                "id": car.pop("listing_id"), "year": car.pop("year_text"),
                "engine": car.pop("engine_text"), "mileage": car.pop("mileage_text"),
                "price": car.pop("price_text"), "images": json.loads(car.pop("images_json")),
            })
            cars.append(car)
        return cars

    def close(self):
        self.connection.close()
