import json
import re

import requests
from bs4 import BeautifulSoup


URL = "https://www.ilmeteo.it/meteo/gioiosa+marea"


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


response = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    timeout=30,
)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
print("url:", response.url)
print("title:", clean(soup.title.get_text() if soup.title else ""))
print("html length:", len(response.text))
print("contains Gioiosa Marea:", "Gioiosa Marea" in response.text)
print("contains nessun risultato:", "nessun risultato" in response.text.lower())

for selector in ["h1", "h2", "table", "[class*=forecast]", "[id*=forecast]", "[class*=giorno]", "[id*=giorno]"]:
    matches = soup.select(selector)
    print(f"\nselector {selector!r}: {len(matches)}")
    for item in matches[:5]:
        print("-", clean(item.get_text(" ", strip=True))[:500])

print("\nforecast-like elements:")
for item in soup.select("[class*=forecast]")[:25]:
    print(item.name, item.get("class"), item.get("id"), "-", clean(item.get_text(" ", strip=True))[:300])

print("\nmeteo-specific classes:")
for item in soup.find_all(class_=re.compile(r"(hour|ora|temp|weather|meteo|giorno|day|forecast)", re.I))[:80]:
    print(item.name, item.get("class"), item.get("id"), "-", clean(item.get_text(" ", strip=True))[:220])

scripts = soup.find_all("script")
print("\nscripts:", len(scripts))
for script in scripts:
    text = script.string or script.get_text()
    if any(term in text for term in ["Gioiosa", "prevision", "temp", "forecast"]):
        print(clean(text)[:1000])
        break

ld_json = []
for script in soup.find_all("script", type="application/ld+json"):
    text = script.string or script.get_text()
    try:
        ld_json.append(json.loads(text))
    except json.JSONDecodeError:
        pass
print("\nld+json count:", len(ld_json))
for item in ld_json[:3]:
    print(json.dumps(item, ensure_ascii=False)[:1000])
