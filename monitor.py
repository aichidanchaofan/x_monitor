import requests
import json
import os
from bs4 import BeautifulSoup

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
    url = f"https://nitter.net/{user}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "lxml")

    tweet = soup.find("div", class_="timeline-item")
    if not tweet:
        return None

    content = tweet.find("div", class_="tweet-content")
    link = tweet.find("a", class_="tweet-link")

    if not content or not link:
        return None

    tweet_id = link["href"]
    text = content.get_text(strip=True)

    return tweet_id, text, f"https://nitter.net{tweet_id}"


def main():
    accounts = load_json(ACCOUNTS_FILE)["users"]
    state = load_json(STATE_FILE)

    for user in accounts:
        try:
            result = fetch_latest_tweet(user)
            if not result:
                continue

            tweet_id, text, url = result

            if state.get(user) == tweet_id:
                continue

            message = f"""📢 新推文

👤 @{user}

📝 {text}

🔗 {url}"""

            send_telegram(message)

            state[user] = tweet_id

        except Exception as e:
            print(f"Error {user}: {e}")

    save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
