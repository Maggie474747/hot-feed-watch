"""
抓取微博热搜榜 Top 10
"""
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 微博热搜的公开 JSON 接口（PC 端 Web 用的）
URL = "https://weibo.com/ajax/side/hotSearch"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://weibo.com/",
    "Accept": "application/json, text/plain, */*",
}

DATA_DIR = Path(__file__).parent / "data"
CST = timezone(timedelta(hours=8))


def format_count(n: int) -> str:
    """微博热度值通常 50万-1000万 量级"""
    if n is None:
        return "—"
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return str(n)


# 微博热搜 label_name 映射成 emoji 标签
LABEL_EMOJI = {
    "新": "🆕",
    "热": "🔥",
    "沸": "💥",
    "爆": "💣",
    "荐": "📌",
}


def fetch_weibo_hot(top_n: int = 10):
    """抓取微博热搜榜前 N 条"""
    print(f"📡  正在抓取微博热搜榜 Top {top_n}...")

    response = requests.get(URL, headers=HEADERS, timeout=10)
    print(f"     HTTP 状态码：{response.status_code}")
    response.raise_for_status()
    data = response.json()

    # 微博 API 返回结构：data.realtime 是热搜数组
    items = data.get("data", {}).get("realtime", [])

    if not items:
        raise RuntimeError("没拿到数据，接口可能变了")

    now = datetime.now(CST)

    normalized = []
    rank = 0
    for item in items:
        # 跳过广告条目（is_ad=1 是广告位，不计入榜单）
        if item.get("is_ad") == 1:
            continue

        rank += 1
        if rank > top_n:
            break

        word = item.get("word", "")
        num = item.get("num", 0)  # 热度值
        label_name = item.get("label_name", "")
        emoji = LABEL_EMOJI.get(label_name, "")
        category = item.get("category", "")

        # 微博搜索链接：用 word_scheme 字段（已经是 %23xxx%23 格式）
        # 如果没有 word_scheme，用 word 包上 # 号
        from urllib.parse import quote
        word_scheme = item.get("word_scheme")
        if word_scheme:
            # word_scheme 通常是 "#xxx#" 形式，直接 quote
            search_query = quote(word_scheme)
        else:
            search_query = quote(f"#{word}#")
        url = f"https://s.weibo.com/weibo?q={search_query}&Refer=top"

        normalized.append({
            "rank": rank,
            "title": f"{emoji} {word}".strip(),
            "author": category if category else "微博热搜",
            "author_avatar": "",
            "view": num,
            "like": 0,
            "reply": 0,
            "share": 0,
            "view_text": format_count(num),
            "like_text": "—",
            "reply_text": "—",
            "share_text": label_name if label_name else "—",
            "url": url,
            "cover": "",
            "bvid": str(item.get("realpos", rank)),
            "label": label_name,
        })

    return {
        "platform": "weibo",
        "platform_name": "微博",
        "fetched_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "videos": normalized,
    }


def save_to_json(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    latest_path = DATA_DIR / "weibo_latest.json"
    archive_path = DATA_DIR / f"weibo_{data['date']}.json"
    for path in [latest_path, archive_path]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾  已保存：{path.relative_to(Path(__file__).parent)}")


def print_preview(data: dict, top_n: int = 5):
    print(f"\n=== 微博热搜 · {data['date']} · 前 {top_n} 条 ===\n")
    for v in data["videos"][:top_n]:
        print(f"#{v['rank']:>2}  {v['title']}")
        print(f"     分类：{v['author']}   标签：{v['share_text']}")
        print(f"     🔥 热度：{v['view_text']}")
        print(f"     🔗 {v['url']}")
        print()


if __name__ == "__main__":
    data = fetch_weibo_hot(top_n=10)
    save_to_json(data)
    print_preview(data, top_n=5)
    print(f"✅  完成！共抓取 {len(data['videos'])} 条")