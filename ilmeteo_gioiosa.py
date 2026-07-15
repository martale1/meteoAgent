import csv
import html
import os
import re
from datetime import datetime

import requests
import telepot
from bs4 import BeautifulSoup


URL = "https://www.ilmeteo.it/meteo/gioiosa+marea"
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
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def text(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""


def fetch_page():
    response = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=30,
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser"), response.url


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


def parse_available_days(soup):
    return parse_daily_forecast(soup)


def parse_summary(soup):
    return {
        "titolo": text(soup.select_one("h1")),
        "aggiornamento": text(soup.select_one(".forecast_update__date")),
        "localita": "Gioiosa Marea",
        "estratto_il": datetime.now().isoformat(timespec="seconds"),
    }


def parse_number(value):
    match = re.search(r"\d+(?:,\d+)?", value or "")
    return float(match.group(0).replace(",", ".")) if match else None


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
        if len(cells) < 7:
            continue

        hour = parse_number(cells[0])
        # Daily pages include the first slot of the next day after 23:00.
        if previous_hour is not None and hour is not None and hour < previous_hour:
            break
        previous_hour = hour

        wind_direction, wind_knots, wind_gust_knots, wind_intensity = parse_wind(cells[5])
        rows.append(
            {
                "giorno": day,
                "ora": cells[0],
                "temperatura_c": parse_number(cells[2]),
                "precipitazioni": cells[3],
                "direzione_vento": wind_direction,
                "vento": wind_knots,
                "vento_max": wind_gust_knots,
                "intensita_vento": wind_intensity,
                "altezza_onda_cm": parse_number(cells[6]),
                "grandine": cells[7] if len(cells) > 7 else "",
                "umidita": cells[8] if len(cells) > 8 else "",
                "pressione_mbar": parse_number(cells[9]) if len(cells) > 9 else None,
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
                "onda_min_cm": None,
                "onda_max_cm": None,
                "vento_min": None,
                "vento_max": None,
                "raffica_max": None,
                "direzione_vento_prevalente": "",
                "direzioni_vento_giorno": "",
            },
        )
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


def send_telegram_message(text_message, parse_mode=None):
    token = os.getenv(TELEGRAM_TOKEN_ENV)
    receiver_id = os.getenv(TELEGRAM_RECEIVER_ENV)
    if not token or not receiver_id:
        print("\nTelegram non inviato: configura TELEGRAM_BOT_TOKEN e TELEGRAM_RECEIVER_ID.")
        return
    bot = telepot.Bot(token)
    bot.sendMessage(receiver_id, text_message, parse_mode=parse_mode)


def direction_text(value):
    return (value or "").replace(" -> ", " > ")


def wave_badge(max_wave_cm):
    if max_wave_cm is None:
        return "⚪"
    if max_wave_cm < 30:
        return "🟢"
    if max_wave_cm <= 50:
        return "🟠"
    return "🔴"


def format_telegram_message(summary, forecast, hourly_by_day):
    lines = [
        "🌊 <b>Meteo Gioiosa Marea</b>",
        html.escape(summary["aggiornamento"]),
        "",
    ]

    for row in forecast:
        hourly = hourly_by_day.get(row["giorno"].lower())
        title = html.escape(row["giorno"])
        temp = f'{html.escape(row["temp_min_c"])}-{html.escape(row["temp_max_c"])} °C'

        if not hourly:
            lines.extend([f"📅 <b>{title}</b>", f"🌡️ Temp: {temp}", ""])
            continue

        badge = wave_badge(hourly["onda_max_cm"])
        wave_range = html.escape(range_text(hourly["onda_min_cm"], hourly["onda_max_cm"], "cm"))
        wind_range = html.escape(range_text(hourly["vento_min"], hourly["vento_max"]))
        gust = f'{hourly["raffica_max"]:.0f}' if hourly["raffica_max"] is not None else "n/d"
        directions = html.escape(direction_text(hourly["direzioni_vento_giorno"]))

        lines.extend(
            [
                f"📅 <b>{title}</b>",
                f"🌡️ Temp: {temp}",
                f"{badge} 🌊 Onde: <b>{wave_range}</b>",
                f"💨 Vento: {wind_range}  max {html.escape(gust)}",
                f"🧭 Dir: {directions}",
                "",
            ]
        )

    lines.extend(
        [
            "🔗 <a href=\"https://www.ilmeteo.it/meteo/gioiosa+marea\">Apri pagina iLMeteo</a>",
        ]
    )
    return "\n".join(lines).strip()


def main():
    load_env_file()
    soup, final_url = fetch_page()
    summary = parse_summary(soup)
    forecast = parse_available_days(soup)
    hourly_rows = []
    for day in forecast:
        day_soup, _ = fetch_soup(day["url"])
        hourly_rows.extend(parse_hourly_forecast(day_soup, day["giorno"]))
    hourly_daily = summarize_hourly_by_day(hourly_rows)
    hourly_by_day = {row["giorno"].lower(): row for row in hourly_daily}

    print("URL finale:", final_url)
    print("Titolo:", summary["titolo"])
    print("Aggiornamento:", summary["aggiornamento"])
    print()
    output_lines = [
        summary["titolo"],
        summary["aggiornamento"],
        "",
    ]
    for row in forecast:
        hourly = hourly_by_day.get(row["giorno"].lower())
        if hourly:
            wave_range = range_text(hourly["onda_min_cm"], hourly["onda_max_cm"], "cm")
            wind_range = range_text(hourly["vento_min"], hourly["vento_max"])
            gust = f'{hourly["raffica_max"]:.0f}' if hourly["raffica_max"] is not None else "n/d"
            line = (
                f'{row["giorno"]:>8}: {row["temp_min_c"]} / {row["temp_max_c"]} °C, '
                f"onde {wave_range}, vento {wind_range} (max {gust}), "
                f'dir {hourly["direzioni_vento_giorno"]}'
            )
        else:
            line = f'{row["giorno"]:>8}: {row["temp_min_c"]} / {row["temp_max_c"]} °C'
        print(line)
        output_lines.append(line)

    with open("gioiosa_marea_ilmeteo.csv", "w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "giorno",
            "temp_min_c",
            "temp_max_c",
            "onda_min_cm",
            "onda_max_cm",
            "vento_min",
            "vento_max",
            "raffica_max",
            "direzione_vento_prevalente",
            "direzioni_vento_giorno",
            "url",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in forecast:
            hourly = hourly_by_day.get(row["giorno"].lower(), {})
            combined = {**hourly, **row}
            writer.writerow(combined)

    with open("gioiosa_marea_orario_ilmeteo.csv", "w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "giorno",
            "ora",
            "temperatura_c",
            "precipitazioni",
            "altezza_onda_cm",
            "direzione_vento",
            "vento",
            "vento_max",
            "intensita_vento",
            "grandine",
            "umidita",
            "pressione_mbar",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(hourly_rows)

    telegram_message = format_telegram_message(summary, forecast, hourly_by_day)
    send_telegram_message(telegram_message, parse_mode="HTML")
    print("\nMessaggio Telegram inviato.")


if __name__ == "__main__":
    main()
