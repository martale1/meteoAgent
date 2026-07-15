import re

import requests
from bs4 import BeautifulSoup


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


for url in [
    "https://www.ilmeteo.it/meteo/gioiosa+marea",
    "https://www.ilmeteo.it/meteo/gioiosa+marea/lungo-termine",
]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    print("\n", response.url)
    for link in soup.select(".forecast_day_selector__list__item__link"):
        print(f"{clean(link.get_text(' ', strip=True))} => {link.get('href')}")
