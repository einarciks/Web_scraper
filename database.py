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
    text = str(value).replace("\u00a0", " ")
    if not decimal:
        # SS.lv uses "," and spaces as thousands separators, e.g. "4,550 \u20ac".
        match = re.search(r"\d+", text.replace(",", "").replace(" ", ""))
        return int(match.group()) if match else None
    match = re.search(r"\d+(?:\.\d+)?", text.replace(",", ".").replace(" ", ""))
    return float(match.group()) if match else None


# SS.lv stores some colors with typos, so the UI label maps to the stored prefix.
COLOR_PREFIXES = {"Light blue": "Ligh"}


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
        self._repair_numbers()

    def _repair_numbers(self):
        """Re-parse numeric columns of rows saved by an older, buggy parser."""
        rows = self.connection.execute(
            "SELECT listing_id, year_text, year, mileage_text, mileage, price_text, price FROM cars"
        ).fetchall()
        updates = []
        for row in rows:
            fixed = (_number(row["year_text"]), _number(row["mileage_text"]), _number(row["price_text"]))
            if fixed != (row["year"], row["mileage"], row["price"]):
                updates.append((*fixed, row["listing_id"]))
        if updates:
            self.connection.executemany(
                "UPDATE cars SET year = ?, mileage = ?, price = ? WHERE listing_id = ?", updates
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
        if body_type:
            where.append(f"body_type IN ({','.join('?' for _ in body_type)})")
            params.extend(body_type)
        # Gearbox is stored as e.g. "Automatic 6 speed", so match by prefix.
        if gearbox:
            where.append("(" + " OR ".join("gearbox LIKE ? COLLATE NOCASE" for _ in gearbox) + ")")
            params.extend(f"{value}%" for value in gearbox)
        if color:
            where.append("(" + " OR ".join("color LIKE ? COLLATE NOCASE" for _ in color) + ")")
            params.extend(f"{COLOR_PREFIXES.get(value, value)}%" for value in color)

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
