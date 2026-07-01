import os
import json
import time
import requests

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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False
        }, timeout=10)
    except Exception as e:
        print("[TELEGRAM ERROR]", e)


# -----------------------------
# 获取 guest token（关键）
# -----------------------------
def get_guest_token():
    headers = {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAA",  # X 公共 guest token机制
        "user-agent": "Mozilla/5.0",
    }

    r = requests.post(
        "https://api.twitter.com/1.1/guest/activate.json",
        headers=headers,
        timeout=10
    )

    if r.status_code != 200:
        print("[GUEST TOKEN FAIL]", r.text)
        return None

    return r.json()["guest_token"]


# -----------------------------
# 获取 timeline（核心）
# -----------------------------
def fetch_latest(user, guest_token):
    try:
        url = f"https://api.twitter.com/2/timeline/profile/{user}.json?tweet_mode=extended"

        headers = {
            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAA",
            "x-guest-token": guest_token,
            "user-agent": "Mozilla/5.0",
        }

        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            print("[FETCH FAIL]", r.status_code)
            return None

        data = r.json()

        instructions = data.get("timeline", {}).get("instructions", [])

        for ins in instructions:
            entries = ins.get("entries", [])
            for e in entries:
                content = e.get("content", {})
                item = content.get("itemContent", {})
                tweet = item.get("tweet_results", {}).get("result", {})

                legacy = tweet.get("legacy", {})
                text = legacy.get("full_text")

                if not text:
                    continue

                tweet_id = legacy.get("id_str")

                return tweet_id, text, f"https://x.com/{user}/status/{tweet_id}"

        return None

    except Exception as e:
        print("[ERROR]", e)
        return None


# -----------------------------
# 主逻辑
# -----------------------------
def main():
    print("===== V6 X MONITOR START =====")

    accounts = load_json(ACCOUNTS_FILE)["users"]
    state = load_json(STATE_FILE)

    print("Accounts:", accounts)

    guest_token = get_guest_token()

    if not guest_token:
        print("NO GUEST TOKEN")
        return

    for user in accounts:
        print(f"[FETCH] {user}")

        result = fetch_latest(user, guest_token)

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
