"""
抓取抖音热搜榜 Top 10
"""
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

URL = "https://www.douyin.com/aweme/v1/hot/search/list/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json, text/plain, */*",
}

DATA_DIR = Path(__file__).parent / "data"
CST = timezone(timedelta(hours=8))

# label 值映射（抖音内部标签）
LABEL_TEXT = {
    0: "",
    1: "🔥",   # 热
    2: "🆕",   # 新
    3: "🔥",   # 热
    4: "💥",   # 爆
    5: "📌",   # 荐
}


def format_count(n: int) -> str:
    if not n:
        return "—"
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return str(n)


def fetch_douyin_hot(top_n: int = 10):
    print(f"📡  正在抓取抖音热搜榜 Top {top_n}...")

    response = requests.get(URL, headers=HEADERS, timeout=15)
    print(f"     HTTP 状态码：{response.status_code}")
    response.raise_for_status()

    data = response.json()
    items = data.get("data", {}).get("word_list", [])

    if not items:
        raise RuntimeError("没拿到数据，接口可能变了")

    now = datetime.now(CST)

    normalized = []
    for item in items[:top_n]:
        word = item.get("word", "")
        hot_value = item.get("hot_value", 0)
        label = item.get("label", 0)
        emoji = LABEL_TEXT.get(label, "")
        position = item.get("position", len(normalized) + 1)

        # 封面图：word_cover.url_list[0]
        cover = ""
        word_cover = item.get("word_cover") or {}
        url_list = word_cover.get("url_list") or []
        if url_list:
            cover = url_list[0]

        search_url = f"https://www.douyin.com/search/{requests.utils.quote(word)}"

        normalized.append({
            "rank": position,
            "title": f"{emoji} {word}".strip(),
            "author": "抖音热搜",
            "author_avatar": "",
            "view": hot_value,
            "like": 0,
            "reply": 0,
            "share": 0,
            "view_text": format_count(hot_value),
            "like_text": "—",
            "reply_text": "—",
            "share_text": "—",
            "url": search_url,
            "cover": cover,
            "bvid": item.get("sentence_id", ""),
            "label": label,
        })

    return {
        "platform": "douyin",
        "platform_name": "抖音",
        "fetched_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "videos": normalized,
    }


def save_to_json(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    latest_path = DATA_DIR / "douyin_latest.json"
    archive_path = DATA_DIR / f"douyin_{data['date']}.json"
    for path in [latest_path, archive_path]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾  已保存：{path.relative_to(Path(__file__).parent)}")


def print_preview(data: dict, top_n: int = 5):
    print(f"\n=== 抖音热搜 · {data['date']} · 前 {top_n} 条 ===\n")
    for v in data["videos"][:top_n]:
        print(f"#{v['rank']:>2}  {v['title']}")
        print(f"     🔥 热度：{v['view_text']}")
        print(f"     🔗 {v['url']}")
        print()


if __name__ == "__main__":
    try:
        data = fetch_douyin_hot(top_n=10)
        save_to_json(data)
        print_preview(data, top_n=5)
        print(f"✅  完成！共抓取 {len(data['videos'])} 条")
    except Exception as e:
        print(f"⚠️ 抖音抓取失败：{e}")
        raise SystemExit(0)
