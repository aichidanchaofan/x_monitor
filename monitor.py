import os
import json
import requests
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

ACCOUNTS_FILE = "accounts.json"
STATE_FILE = "state.json"


# -----------------------------
# JSON
# -----------------------------
def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -----------------------------
# Telegram
# -----------------------------
def send_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
            timeout=10
        )
    except Exception as e:
        print("[TELEGRAM FAIL]", e)


# -----------------------------
# 方法1：Playwright（主）
# -----------------------------
def fetch_playwright(user):
    try:
        url = f"https://x.com/{user}"

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox"]
            )
            page = browser.new_page()

            print(f"[PLAYWRIGHT] open {url}")
            page.goto(url, timeout=30000)
            page.wait_for_timeout(6000)

            articles = page.query_selector_all("article")

            if not articles:
                browser.close()
                return None

            first = articles[0]
            text = first.inner_text().strip()

            tweet_id = str(hash(text))

            browser.close()

            return tweet_id, text, url

    except Exception as e:
        print("[PLAYWRIGHT ERROR]", e)
        return None


# -----------------------------
# 方法2：静态HTML fallback
# -----------------------------
def fetch_fallback(user):
    try:
        url = f"https://x.com/{user}"
        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        text = soup.get_text()

        if len(text) < 50:
            return None

        tweet_id = str(hash(text[:500]))

        return tweet_id, text[:500], url

    except Exception as e:
        print("[FALLBACK ERROR]", e)
        return None


# -----------------------------
# 多层抓取
# -----------------------------
def fetch_latest(user):
    print(f"[FETCH] {user}")

    # 1. Playwright
    result = fetch_playwright(user)
    if result:
        return result

    print("[FALLBACK] switching...")

    # 2. fallback
    result = fetch_fallback(user)
    if result:
        return result

    return None


# -----------------------------
# 主逻辑
# -----------------------------
def main():
    print("===== V5 PRO START =====")

    accounts = load_json(ACCOUNTS_FILE)["users"]
    state = load_json(STATE_FILE)

    print("Accounts:", accounts)

    for user in accounts:
        result = fetch_latest(user)

        print(f"[DEBUG] {user} -> {result}")

        if not result:
            continue

        tweet_id, text, url = result

        if state.get(user) == tweet_id:
            print(f"[SKIP] {user}")
            continue

        msg = f"""📢 新推文

👤 @{user}

📝 {text[:800]}

🔗 {url}"""

        print(f"[SEND] {user}")
        send_telegram(msg)

        state[user] = tweet_id

    save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
