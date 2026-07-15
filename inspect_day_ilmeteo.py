import re

import requests
from bs4 import BeautifulSoup


URL = "https://www.ilmeteo.it/meteo/gioiosa+marea/5"


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

print("url:", response.url)
print("title:", clean(soup.title.get_text() if soup.title else ""))

table = soup.select_one("table.weather_table")
print("table:", table.get("class") if table else None)
if table:
    print("headers:")
    print([clean(cell.get_text(" ", strip=True)) for cell in table.find_all("th")])
    print("\nrows:")
    for row in table.select("tr")[:20]:
        cells = [clean(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        print(row.get("class"), cells)

print("\nwind/wave classes:")
for item in soup.find_all(class_=re.compile(r"(vento|wind|onda|wave|temp|ora)", re.I))[:80]:
    print(item.name, item.get("class"), item.get("id"), "-", clean(item.get_text(" ", strip=True))[:220])

print("\nforecast_3h cells:")
for row in soup.select("tr.forecast_3h")[:12]:
    cells = [clean(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
    print(row.get("class"), cells)
