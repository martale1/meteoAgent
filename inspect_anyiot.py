import re

import requests
from bs4 import BeautifulSoup


URL = "http://theoiziruam.ddns.net:808/index2.php"


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


response = requests.get(URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

print("url:", response.url)
print("title:", clean(soup.title.get_text() if soup.title else ""))

print("\nTemperature blocks:")
for room in soup.select(".pTempRoom"):
    parent = room.find_parent("div", class_="alarm-status-text")
    if not parent:
        continue
    values = [clean(p.get_text(" ", strip=True)) for p in parent.find_all("p")]
    print(values)

print("\nPower values:")
for box in soup.select(".box-object-power"):
    print(clean(box.get_text(" ", strip=True)))

print("\nAlarm/PIR blocks:")
for title in soup.select(".pTitleAlarm"):
    parent = title.find_parent("div", class_="alarm-status-text")
    if not parent:
        continue
    values = [clean(p.get_text(" ", strip=True)) for p in parent.find_all("p")]
    print(values)
