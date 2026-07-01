import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

ACCOUNTS_FILE = "accounts.json"
STATE_FILE = "state.json"


# -----------------------------
# JSON 工具
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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": False
            },
            timeout=10
        )
    except Exception as e:
        print("[TELEGRAM ERROR]", e)


# -----------------------------
# ⭐ 核心抓取（稳定版）
# -----------------------------
def fetch_latest_tweet(user):
    url = f"https://x.com/{user}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox"]
            )

            page = browser.new_page()
            print(f"[OPEN] {url}")

            page.goto(url, timeout=30000)
            page.wait_for_timeout(6000)

            tweets = page.locator("article").all()

            for t in tweets:
                try:
                    text_blocks = t.locator("[data-testid='tweetText']")

                    if text_blocks.count() == 0:
                        continue

                    text = text_blocks.first.inner_text().strip()

                    # ❌ 过滤 pinned / 空内容
                    if not text or "Pinned" in text:
                        continue

                    tweet_id = str(hash(text))

                    browser.close()
                    return tweet_id, text, url

                except:
                    continue

            browser.close()
            return None

    except Exception as e:
        print("[PLAYWRIGHT ERROR]", e)
        return None


# -----------------------------
# 主逻辑
# -----------------------------
def main():
    print("===== V5.8 X MONITOR START =====")
    print(f"[HEARTBEAT] {time.time()}")

    accounts = load_json(ACCOUNTS_FILE)["users"]
    state = load_json(STATE_FILE)

    print("Accounts:", accounts)

    for user in accounts:
        result = fetch_latest_tweet(user)

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
