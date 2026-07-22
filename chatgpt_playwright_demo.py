import argparse
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


CHATGPT_URL = "https://chatgpt.com/"
PROFILE_DIR = Path("playwright_chatgpt_profile")


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
    page.wait_for_timeout(3000)
    try:
        page.locator("[data-testid='send-button']").wait_for(state="visible", timeout=120000)
    except PlaywrightTimeoutError:
        pass

    messages = page.locator("[data-message-author-role='assistant']")
    count = messages.count()
    if count == 0:
        return ""
    return messages.nth(count - 1).inner_text(timeout=10000)


def main():
    parser = argparse.ArgumentParser(description="Demo Playwright per una chat manuale con ChatGPT.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Scrivi una frase breve di test.",
        help="Messaggio da inviare a ChatGPT.",
    )
    parser.add_argument(
        "--login-only",
        action="store_true",
        help="Apre ChatGPT e lascia il browser aperto per fare login manuale.",
    )
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1400, "height": 900},
        )
        page = browser.new_page()
        page.goto(CHATGPT_URL, wait_until="domcontentloaded")

        if args.login_only:
            input("Fai login nel browser aperto, poi premi INVIO qui per chiudere...")
            browser.close()
            return

        send_prompt(page, args.prompt)
        response = wait_for_response(page)
        print("\n--- Risposta ChatGPT ---")
        print(response or "Nessuna risposta trovata.")
        browser.close()


if __name__ == "__main__":
    main()
