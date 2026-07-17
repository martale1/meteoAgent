import html
import os
import re
from dataclasses import dataclass
from datetime import datetime

import requests
import telepot


URL = "http://theoiziruam.ddns.net:808/index2.php"
MAX_SENSOR_AGE_MINUTES = 45
SEND_OK_NOTIFICATION = False
TELEGRAM_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
TELEGRAM_RECEIVER_ENV = "TELEGRAM_RECEIVER_ID"


@dataclass
class Sensor:
    house: str
    ambiente: str
    label: str
    temperature: str
    humidity: str
    updated_at: datetime


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


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def fetch_page():
    response = requests.get(URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.text


def parse_page_time(page_html):
    match = re.search(r"Date and Time:\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})", page_html)
    if not match:
        return datetime.now()
    return datetime.strptime(f"{match.group(1)} {match.group(2)}", "%Y-%m-%d %H:%M:%S")


def parse_sensors(page_html):
    pattern = re.compile(
        r"jsMeteo\.php\?house=(?P<house>[^&'\"]+).*?ambiente=(?P<ambiente>[^'\"]+)"
        r".*?<p class=['\"]pTempRoom['\"]>\s*(?P<label>.*?)\s*</p>"
        r".*?<p class=['\"]pTempValue['\"]>\s*(?P<temperature>.*?)\s*</p>"
        r".*?<p class=\"pText\">\s*(?P<humidity>.*?)\s*</p>"
        r".*?<p class=\"pText\">\s*(?P<time>\d{2}:\d{2}:\d{2})\s*</p>"
        r".*?<p class=\"pText\"[^>]*>\s*(?P<date>\d{4}-\d{2}-\d{2})\s*</p>",
        re.DOTALL,
    )

    sensors = []
    for match in pattern.finditer(page_html):
        updated_at = datetime.strptime(f"{match.group('date')} {match.group('time')}", "%Y-%m-%d %H:%M:%S")
        sensors.append(
            Sensor(
                house=clean(match.group("house")),
                ambiente=clean(match.group("ambiente")),
                label=clean(match.group("label")),
                temperature=clean(match.group("temperature")).replace("°C", " °C"),
                humidity=clean(match.group("humidity")),
                updated_at=updated_at,
            )
        )
    return sensors


def sensor_age_minutes(reference_time, sensor):
    return int((reference_time - sensor.updated_at).total_seconds() // 60)


def format_duration(minutes):
    if minutes < 60:
        return f"{minutes} min"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m"


def send_telegram_message(text_message):
    token = os.getenv(TELEGRAM_TOKEN_ENV)
    receiver_id = os.getenv(TELEGRAM_RECEIVER_ENV)
    if not token or not receiver_id:
        print("Telegram non inviato: configura TELEGRAM_BOT_TOKEN e TELEGRAM_RECEIVER_ID.")
        return
    bot = telepot.Bot(token)
    bot.sendMessage(receiver_id, text_message, parse_mode="HTML")


def build_problem_message(reference_time, sensors, stale_sensors, error=None):
    lines = [
        "🔴 <b>AnyIOT healthcheck</b>",
        f"Controllo: {reference_time:%Y-%m-%d %H:%M:%S}",
        "",
    ]

    if error:
        lines.extend(["<b>Errore pagina</b>", html.escape(error)])
        return "\n".join(lines)

    if not sensors:
        lines.append("Nessun sensore temperatura/umidità estratto dalla pagina.")
        return "\n".join(lines)

    if len(stale_sensors) == len(sensors):
        lines.append("⚠️ <b>Tutti i sensori risultano non aggiornati.</b>")
    else:
        lines.append(f"⚠️ Sensori non aggiornati: <b>{len(stale_sensors)}/{len(sensors)}</b>")

    lines.append("")
    for sensor, age in stale_sensors:
        lines.extend(
            [
                f"📍 <b>{html.escape(sensor.house)} / {html.escape(sensor.label)}</b>",
                f"Ultimo update: {sensor.updated_at:%Y-%m-%d %H:%M:%S}",
                f"Ritardo: <b>{format_duration(age)}</b>",
                f"Temp/Umidità: {html.escape(sensor.temperature)} / {html.escape(sensor.humidity)}",
                "",
            ]
        )

    lines.append(f"🔗 {html.escape(URL)}")
    return "\n".join(lines).strip()


def build_ok_message(reference_time, sensors):
    return "\n".join(
        [
            "🟢 <b>AnyIOT OK</b>",
            f"Controllo: {reference_time:%Y-%m-%d %H:%M:%S}",
            f"Sensori aggiornati: {len(sensors)}",
            f"Soglia: {MAX_SENSOR_AGE_MINUTES} min",
        ]
    )


def main():
    load_env_file()
    try:
        page_html = fetch_page()
        reference_time = parse_page_time(page_html)
        sensors = parse_sensors(page_html)
        stale_sensors = [
            (sensor, sensor_age_minutes(reference_time, sensor))
            for sensor in sensors
            if sensor_age_minutes(reference_time, sensor) > MAX_SENSOR_AGE_MINUTES
        ]
    except Exception as exc:
        reference_time = datetime.now()
        message = build_problem_message(reference_time, [], [], error=str(exc))
        print(message)
        send_telegram_message(message)
        return

    print(f"Controllo AnyIOT: {reference_time:%Y-%m-%d %H:%M:%S}")
    print(f"Sensori trovati: {len(sensors)}")
    print(f"Sensori non aggiornati: {len(stale_sensors)}")

    if stale_sensors:
        message = build_problem_message(reference_time, sensors, stale_sensors)
        print(message)
        send_telegram_message(message)
    elif SEND_OK_NOTIFICATION:
        message = build_ok_message(reference_time, sensors)
        print(message)
        send_telegram_message(message)
    else:
        print("Tutto OK: nessuna notifica inviata.")


if __name__ == "__main__":
    main()
