import csv
import html
import os
import re
import sys
from datetime import datetime

import requests
import telepot
from bs4 import BeautifulSoup

DEFAULT_CITY = "cusago"
TELEGRAM_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
TELEGRAM_RECEIVER_ENV = "TELEGRAM_RECEIVER_ID"


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if "#" in value:
                value = value.split("#", 1)[0]
            os.environ[key.strip()] = value.strip().strip("'\"")


def get_city_config():
    load_env_file()
    city_input = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        city_input = " ".join(sys.argv[1:])
    elif os.getenv("METEO_CITY"):
        city_input = os.getenv("METEO_CITY")
    else:
        city_input = DEFAULT_CITY

    city_clean = city_input.strip().lower().replace(" ", "+")
    city_name = city_input.strip().title()

    url = f"https://www.ilmeteo.it/meteo/{city_clean}" if len(sys.argv) > 1 else (os.getenv("METEO_URL") or f"https://www.ilmeteo.it/meteo/{city_clean}")
    return city_name, city_clean, url


def text(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""


def fetch_soup(url):
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=30,
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser"), response.url


def parse_daily_forecast(soup):
    rows = []
    for link in soup.select(".forecast_day_selector__list__item__link"):
        date_label = text(link.select_one(".forecast_day_selector__list__item__link__date"))
        temp_min = text(link.select_one(".forecast_day_selector__list__item__link__values__lower"))
        temp_max = text(link.select_one(".forecast_day_selector__list__item__link__values__higher"))
        if not date_label or not temp_min or not temp_max:
            continue
        rows.append(
            {
                "giorno": date_label,
                "temp_min_c": temp_min.replace("°", ""),
                "temp_max_c": temp_max.replace("°", ""),
                "url": link.get("href", ""),
            }
        )
    return rows


def parse_summary(soup, city_name):
    title = text(soup.select_one("h1")) or f"Meteo {city_name}"
    return {
        "titolo": title,
        "aggiornamento": text(soup.select_one(".forecast_update__date")),
        "localita": city_name,
        "estratto_il": datetime.now().isoformat(timespec="seconds"),
    }


def parse_number(value):
    if not value:
        return None
    match = re.search(r"\d+(?:,\d+)?|\d+(?:\.\d+)?", value)
    return float(match.group(0).replace(",", ".")) if match else None


def parse_precipitation(value):
    if not value or "assenti" in value.lower():
        return 0.0, "- assenti -"
    val = parse_number(value)
    return (val if val is not None else 0.0), value


def parse_hail(value):
    if not value:
        return 0
    val = parse_number(value)
    return int(val) if val is not None else 0


def parse_wind(value):
    match = re.match(
        r"(?P<direction>[A-Za-z.]+)\s+(?P<speed>\d+(?:,\d+)?)(?:\s+(?P<gust>\d+(?:,\d+)?))?(?:\s+(?P<intensity>.+))?",
        value or "",
    )
    if not match:
        return "", None, None, value
    return (
        match.group("direction"),
        float(match.group("speed").replace(",", ".")),
        float(match.group("gust").replace(",", ".")) if match.group("gust") else None,
        match.group("intensity") or "",
    )


def parse_hourly_forecast(soup, day):
    rows = []
    previous_hour = None
    forecast_rows = soup.select("tr.forecast_1h") or soup.select("tr.forecast_3h")

    for row in forecast_rows:
        cells = [text(cell) for cell in row.find_all("td")]
        if len(cells) < 6:
            continue

        hour = parse_number(cells[0])
        if previous_hour is not None and hour is not None and hour < previous_hour:
            break
        previous_hour = hour

        temp_c = parse_number(cells[2])
        precip_mm, precip_text = parse_precipitation(cells[3])

        wind_cell = cells[5] if (len(cells) > 5 and not cells[4]) else cells[4]
        wind_direction, wind_knots, wind_gust_knots, wind_intensity = parse_wind(wind_cell)

        wave_cm = None
        hail_pct = 0
        
        # In Gioiosa Marea (mare): cells[6] e l'altezza dell'onda (es: '15'), cells[7] e la Grandine ('0%')
        # In Cusago (entroterra): cells[6] e direttamente la Grandine (es: '31%')
        if len(cells) > 6:
            c6 = cells[6]
            if "%" not in c6 and parse_number(c6) is not None:
                wave_cm = parse_number(c6)
                if len(cells) > 7 and "%" in cells[7]:
                    hail_pct = parse_hail(cells[7])
            elif "%" in c6:
                hail_pct = parse_hail(c6)

        rows.append(
            {
                "giorno": day,
                "ora": cells[0],
                "temperatura_c": temp_c,
                "precipitazioni_mm": precip_mm,
                "precipitazioni_testo": precip_text,
                "direzione_vento": wind_direction,
                "vento": wind_knots,
                "vento_max": wind_gust_knots,
                "intensita_vento": wind_intensity,
                "altezza_onda_cm": wave_cm,
                "grandine_pct": hail_pct,
            }
        )
    return rows


def summarize_hourly_by_day(rows):
    summaries = {}
    for row in rows:
        day = row["giorno"]
        if not day:
            continue
        summary = summaries.setdefault(
            day,
            {
                "giorno": day,
                "precipitazioni_tot_mm": 0.0,
                "grandine_max_pct": 0,
                "onda_min_cm": None,
                "onda_max_cm": None,
                "vento_min": None,
                "vento_max": None,
                "raffica_max": None,
                "direzione_vento_prevalente": "",
                "direzioni_vento_giorno": "",
            },
        )
        summary["precipitazioni_tot_mm"] += row.get("precipitazioni_mm", 0.0)
        summary["grandine_max_pct"] = max(summary["grandine_max_pct"], row.get("grandine_pct", 0))

        for source, min_key, max_key in [
            ("altezza_onda_cm", "onda_min_cm", "onda_max_cm"),
            ("vento", "vento_min", "vento_max"),
        ]:
            value = row[source]
            if value is None:
                continue
            summary[min_key] = value if summary[min_key] is None else min(summary[min_key], value)
            summary[max_key] = value if summary[max_key] is None else max(summary[max_key], value)

        gust = row["vento_max"]
        if gust is not None:
            summary["raffica_max"] = gust if summary["raffica_max"] is None else max(summary["raffica_max"], gust)

    for day, summary in summaries.items():
        day_rows = [row for row in rows if row["giorno"] == day]
        summary["direzione_vento_prevalente"] = most_common(row["direzione_vento"] for row in day_rows)
        summary["direzioni_vento_giorno"] = compact_sequence(row["direzione_vento"] for row in day_rows)
    return list(summaries.values())


def most_common(values):
    counts = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return max(counts, key=counts.get) if counts else ""


def compact_sequence(values):
    sequence = []
    for value in values:
        if not value:
            continue
        if not sequence or sequence[-1] != value:
            sequence.append(value)
    return " -> ".join(sequence)


def range_text(min_value, max_value, unit=""):
    if min_value is None or max_value is None:
        return "n/d"
    suffix = f" {unit}" if unit else ""
    return f"{min_value:.0f}-{max_value:.0f}{suffix}"


def wave_badge(max_wave_cm):
    if max_wave_cm is None:
        return ""
    if max_wave_cm < 30:
        return "🟢"
    if max_wave_cm <= 50:
        return "🟠"
    return "🔴"


def temp_badge(temp_max_c):
    try:
        val = float(str(temp_max_c).replace("°", "").strip())
    except (ValueError, TypeError):
        return "🌡️"
    if val <= 15:
        return "🔵"  # Freddo (<= 15°C)
    if val <= 25:
        return "🟢"  # Mite (16 - 25°C)
    if val <= 32:
        return "🟠"  # Caldo (26 - 32°C)
    return "🔴"      # Molto caldo (> 32°C)


def weather_precipitation_line(precip_tot_mm, snow_cm=0, fog=False):
    if snow_cm > 0:
        return f"❄️ Neve: <b>{snow_cm:.1f} cm</b>"
    if fog:
        return "🌫️ Nebbia: <b>Presente</b>"
    
    if precip_tot_mm <= 0:
        return "☀️ Precipitazioni: <i>Assenti</i>"
    if precip_tot_mm <= 2.0:
        return f"🟡 ☔ Pioggia debole: <b>{precip_tot_mm:.1f} mm</b>"
    if precip_tot_mm <= 5.0:
        return f"🟠 🌧️ Pioggia moderata: <b>{precip_tot_mm:.1f} mm</b>"
    return f"🔴 ⛈️ Pioggia forte: <b>{precip_tot_mm:.1f} mm</b>"


def hail_badge(hail_max_pct):
    if hail_max_pct <= 0:
        return ""
    if hail_max_pct <= 25:
        return "🟡"  # Rischio basso (<= 25%)
    if hail_max_pct <= 50:
        return "🟠"  # Rischio medio (<= 50%)
    return "🔴"      # Rischio alto (> 50%)


def send_telegram_message(text_message, parse_mode=None):
    token = (
        os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("TELEGRAM_BOT_TOKEN_CH1")
        or os.getenv("TELEGRAM_BOT_TOKEN_DEFAULT")
    )
    receiver_id = os.getenv(TELEGRAM_RECEIVER_ENV)
    if not token or not receiver_id:
        print("\nTelegram non inviato: configura TELEGRAM_BOT_TOKEN (o TELEGRAM_BOT_TOKEN_CH1) e TELEGRAM_RECEIVER_ID in .env.")
        return
    bot = telepot.Bot(token)
    bot.sendMessage(receiver_id, text_message, parse_mode=parse_mode)


def format_telegram_message(summary, forecast, hourly_by_day, city_name, city_url):
    lines = [
        f"🌤️ <b>Meteo {city_name}</b>",
        html.escape(summary["aggiornamento"]),
        "",
    ]

    for row in forecast:
        hourly = hourly_by_day.get(row["giorno"].lower())
        title = html.escape(row["giorno"])
        temp = f'{html.escape(row["temp_min_c"])}-{html.escape(row["temp_max_c"])} °C'
        t_badge = temp_badge(row["temp_max_c"])

        if not hourly:
            lines.extend([f"📅 <b>{title}</b>", f"{t_badge} 🌡️ Temp: <b>{temp}</b>", ""])
            continue

        day_lines = [
            f"📅 <b>{title}</b>",
            f"{t_badge} 🌡️ Temp: <b>{temp}</b>",
        ]

        precip_tot = hourly.get("precipitazioni_tot_mm", 0.0)
        snow_tot = hourly.get("neve_tot_cm", 0.0)
        fog_found = hourly.get("nebbia_presente", False)

        p_line = weather_precipitation_line(precip_tot, snow_cm=snow_tot, fog=fog_found)
        day_lines.append(p_line)

        hail_max = hourly.get("grandine_max_pct", 0)
        if hail_max > 0:
            h_badge = hail_badge(hail_max)
            day_lines.append(f"{h_badge} 🧊 Grandine: <b>{hail_max}% max</b>")

        if hourly.get("onda_max_cm") is not None:
            w_badge = wave_badge(hourly["onda_max_cm"])
            wave_range = html.escape(range_text(hourly["onda_min_cm"], hourly["onda_max_cm"], "cm"))
            day_lines.append(f"{w_badge} 🌊 Onde: <b>{wave_range}</b>")

        wind_range = html.escape(range_text(hourly["vento_min"], hourly["vento_max"]))
        gust = f'{hourly["raffica_max"]:.0f}' if hourly["raffica_max"] is not None else "n/d"
        directions = html.escape(hourly["direzioni_vento_giorno"].replace(" -> ", " > "))

        day_lines.append(f"💨 Vento: {wind_range} max {html.escape(gust)}")
        if directions:
            day_lines.append(f"🧭 Dir: {directions}")

        day_lines.append("")
        lines.extend(day_lines)

    lines.append(f'🔗 <a href="{city_url}">Apri pagina iLMeteo ({city_name})</a>')
    return "\n".join(lines).strip()


def main():
    city_name, city_clean, city_url = get_city_config()
    print(f"=== Scraping iLMeteo per: {city_name} ===")
    print(f"URL: {city_url}\n")

    soup, final_url = fetch_soup(city_url)
    summary = parse_summary(soup, city_name)
    forecast = parse_daily_forecast(soup)
    
    hourly_rows = []
    for day in forecast:
        if day.get("url"):
            day_soup, _ = fetch_soup(day["url"])
            hourly_rows.extend(parse_hourly_forecast(day_soup, day["giorno"]))

    hourly_daily = summarize_hourly_by_day(hourly_rows)
    hourly_by_day = {row["giorno"].lower(): row for row in hourly_daily}

    for row in forecast:
        hourly = hourly_by_day.get(row["giorno"].lower(), {})
        precip = f"{hourly.get('precipitazioni_tot_mm', 0.0):.1f}mm"
        hail = f", Grandine {hourly.get('grandine_max_pct', 0)}%" if hourly.get('grandine_max_pct', 0) > 0 else ""
        wave = f", Onde {range_text(hourly.get('onda_min_cm'), hourly.get('onda_max_cm'), 'cm')}" if hourly.get('onda_max_cm') is not None else ""
        print(f"{row['giorno']:>8}: {row['temp_min_c']} / {row['temp_max_c']} °C | Pioggia: {precip}{hail}{wave}")

    csv_prefix = city_clean.replace("+", "_")
    with open(f"{csv_prefix}_ilmeteo.csv", "w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "giorno", "temp_min_c", "temp_max_c", "precipitazioni_tot_mm", "grandine_max_pct",
            "onda_min_cm", "onda_max_cm", "vento_min", "vento_max", "raffica_max",
            "direzione_vento_prevalente", "direzioni_vento_giorno", "url"
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in forecast:
            hourly = hourly_by_day.get(row["giorno"].lower(), {})
            combined = {**hourly, **row}
            writer.writerow({k: combined.get(k, "") for k in fieldnames})

    telegram_message = format_telegram_message(summary, forecast, hourly_by_day, city_name, final_url)
    send_telegram_message(telegram_message, parse_mode="HTML")
    print(f"\nMessaggio Telegram generato e pronto per {city_name}.")


if __name__ == "__main__":
    main()
