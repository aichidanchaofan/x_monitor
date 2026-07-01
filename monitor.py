import requests
import feedparser
import json
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

ACCOUNTS_FILE = "accounts.json"
STATE_FILE = "state.json"


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": False
    })


def fetch_latest_tweet(user):
    url = f"https://rsshub.app/twitter/user/{user}"

    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            return None

        entry = feed.entries[0]

        tweet_id = entry.link
        text = entry.title

        return tweet_id, text, entry.link

    except Exception as e:
        print(f"RSS error {user}: {e}")
        return None


def main():
    print("===== V2 X MONITOR START =====")

    accounts = load_json(ACCOUNTS_FILE)["users"]
    state = load_json(STATE_FILE)

    print("Accounts:", accounts)
    print("State:", state)

    for user in accounts:
        result = fetch_latest_tweet(user)

        print(f"[DEBUG] {user} -> {result}")

        if not result:
            continue

        tweet_id, text, url = result

        if state.get(user) == tweet_id:
            print(f"[SKIP] {user} no update")
            continue

        message = f"""📢 新推文

👤 @{user}

📝 {text}

🔗 {url}"""

        print(f"[SEND] {user}")
        send_telegram(message)

        state[user] = tweet_id

    save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
