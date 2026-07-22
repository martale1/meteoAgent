import argparse
import os
from pathlib import Path

import telepot
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


CHATGPT_URL = "https://chatgpt.com/"
PROFILE_DIR = Path("playwright_chatgpt_profile")
CHROME_PROFILE_DIR = Path("chrome_chatgpt_profile")
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


def find_prompt_box(page):
    selectors = [
        "textarea[data-testid='prompt-textarea']",
        "div[contenteditable='true'][data-testid='prompt-textarea']",
        "textarea",
        "div[contenteditable='true']",
    ]
    for selector in selectors:
        locator = page.locator(selector).last
        try:
            locator.wait_for(state="visible", timeout=5000)
            return locator
        except PlaywrightTimeoutError:
            continue
    raise RuntimeError("Non trovo il campo prompt di ChatGPT. La UI potrebbe essere cambiata o serve login.")


def send_prompt(page, prompt):
    prompt_box = find_prompt_box(page)
    prompt_box.click()
    prompt_box.fill(prompt)
    page.keyboard.press("Enter")


def wait_for_response(page):
    last_text = ""
    stable_reads = 0
    deadline_ms = 180000
    step_ms = 2000
    elapsed_ms = 0

    while elapsed_ms < deadline_ms:
        page.wait_for_timeout(step_ms)
        elapsed_ms += step_ms

        messages = page.locator("[data-message-author-role='assistant']")
        count = messages.count()
        if count == 0:
            continue

        try:
            current_text = messages.nth(count - 1).inner_text(timeout=5000).strip()
        except PlaywrightError:
            continue

        if current_text and current_text == last_text:
            stable_reads += 1
        else:
            stable_reads = 0
            last_text = current_text

        if last_text and stable_reads >= 2:
            return last_text

    return last_text


def open_chatgpt_page(context_or_browser):
    page = context_or_browser.new_page()
    page.goto(CHATGPT_URL, wait_until="domcontentloaded")
    return page


def run_in_page(page, prompt, login_only):
    if login_only:
        input("Fai login nel browser aperto, poi premi INVIO qui per chiudere...")
        return

    send_prompt(page, prompt)
    response = wait_for_response(page)
    print("\n--- Risposta ChatGPT ---")
    print(response or "Nessuna risposta trovata.")
    return response


def send_telegram_message(text_message):
    token = os.getenv(TELEGRAM_TOKEN_ENV)
    receiver_id = os.getenv(TELEGRAM_RECEIVER_ENV)
    if not token or not receiver_id:
        print("\nTelegram non inviato: configura TELEGRAM_BOT_TOKEN e TELEGRAM_RECEIVER_ID.")
        return
    bot = telepot.Bot(token)
    bot.sendMessage(receiver_id, text_message)


def main():
    load_env_file()
    parser = argparse.ArgumentParser(description="Demo Playwright per una chat manuale con ChatGPT.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Cerca news di oggi su vodafone .",
        help="Messaggio da inviare a ChatGPT.",
    )
    parser.add_argument(
        "--login-only",
        action="store_true",
        help="Apre ChatGPT e lascia il browser aperto per fare login manuale.",
    )
    parser.add_argument(
        "--chrome",
        action="store_true",
        help="Usa Google Chrome reale invece del Chromium bundled di Playwright.",
    )
    parser.add_argument(
        "--cdp",
        default="",
        help="Connetti Playwright a un Chrome gia' avviato con remote debugging, es. http://127.0.0.1:9222.",
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Invia la risposta raccolta su Telegram usando TELEGRAM_BOT_TOKEN e TELEGRAM_RECEIVER_ID da .env.",
    )
    args = parser.parse_args()

    with sync_playwright() as p:
        if args.cdp:
            browser = p.chromium.connect_over_cdp(args.cdp)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = open_chatgpt_page(context)
            response = run_in_page(page, args.prompt, args.login_only)
            if args.telegram and response:
                send_telegram_message(response)
                print("\nMessaggio Telegram inviato.")
            return

        launch_options = {
            "user_data_dir": str(CHROME_PROFILE_DIR if args.chrome else PROFILE_DIR),
            "headless": False,
            "viewport": {"width": 1400, "height": 900},
        }
        if args.chrome:
            launch_options["channel"] = "chrome"

        context = p.chromium.launch_persistent_context(**launch_options)
        page = open_chatgpt_page(context)
        response = run_in_page(page, args.prompt, args.login_only)
        if args.telegram and response:
            send_telegram_message(response)
            print("\nMessaggio Telegram inviato.")
        context.close()


if __name__ == "__main__":
    main()
