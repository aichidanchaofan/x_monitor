import requests
import feedparser
import json
import os
import random
import time
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

ACCOUNTS_FILE = "accounts.json"
STATE_FILE = "state.json"

# -----------------------------
# RSSHub 镜像池（关键升级）
# -----------------------------
RSSHUB_NODES = [
    "https://rsshub.app",
    "https://rsshub.pseudoyu.com",
    "https://rsshub.feeded.xyz"
]


# -----------------------------
# 工具函数
# -----------------------------
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
    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False
        }, timeout=10)
    except Exception as e:
        print("[TELEGRAM ERROR]", e)


# -----------------------------
# RSSHub 多节点抓取
# -----------------------------
def fetch_from_rsshub(user):
    nodes = RSSHUB_NODES[:]
    random.shuffle(nodes)

    for node in nodes:
        try:
            url = f"{node}/twitter/user/{user}"
            print(f"[RSSHUB TRY] {url}")

            feed = feedparser.parse(url)

            if feed.entries:
                e = feed.entries[0]
                return e.link, e.title, e.link

        except Exception as e:
            print(f"[RSSHUB FAIL] {node}: {e}")

    return None


# -----------------------------
# Nitter fallback
# -----------------------------
def fetch_from_nitter(user):
    try:
        url = f"https://nitter.net/{user}"
        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=8)
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

    except Exception as e:
        print("[NITTER ERROR]", e)
        return None


# -----------------------------
# 多源统一入口
# -----------------------------
def fetch_latest(user):
    sources = [
        fetch_from_rsshub,
        fetch_from_nitter
    ]

    for src in sources:
        try:
            result = src(user)
            if result:
                print(f"[SOURCE OK] {user} -> {src.__name__}")
                return result
        except Exception as e:
            print(f"[SOURCE FAIL] {src.__name__}: {e}")

    print(f"[ALL SOURCES FAILED] {user}")
    return None


# -----------------------------
# 主逻辑
# -----------------------------
def main():
    print("===== V4 X MONITOR START =====")
    print(f"[HEARTBEAT] {time.time()}")

    accounts = load_json(ACCOUNTS_FILE)["users"]
    state = load_json(STATE_FILE)

    print("Accounts:", accounts)
    print("State before:", state)

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

📝 {text}

🔗 {url}"""

        print(f"[SEND] {user}")
        send_telegram(msg)

        state[user] = tweet_id

    save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
