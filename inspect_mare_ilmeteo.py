import re

import requests
from bs4 import BeautifulSoup


URL = "https://www.ilmeteo.it/mari/meteo-mare/citta/Gioiosa+Marea"


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

print("url:", response.url)
print("title:", clean(soup.title.get_text() if soup.title else ""))
print("tables:", len(soup.find_all("table")))

for table in soup.find_all("table")[:10]:
    print("\nTABLE", table.get("class"), table.get("id"))
    print(clean(table.get_text(" ", strip=True))[:2000])

table = soup.select_one("table.data-table")
if table:
    print("\nfirst rows:")
    for row in table.select("tr")[:20]:
        cells = [clean(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        print("TR", row.get("class"), row.get("data-day"), cells)

print("\nclasses containing mare/onda/vento:")
for item in soup.find_all(class_=re.compile(r"(mare|onda|vento|wind|wave|day|giorno|meteo)", re.I))[:120]:
    print(item.name, item.get("class"), item.get("id"), "-", clean(item.get_text(" ", strip=True))[:300])
