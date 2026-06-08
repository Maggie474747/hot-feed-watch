"""
抓取 YouTube 全球热门视频榜 Top 10（官方 Data API v3）
"""
import json
import os
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
URL = "https://www.googleapis.com/youtube/v3/videos"

PARAMS = {
    "part": "snippet,statistics",
    "chart": "mostPopular",
    "regionCode": "US",
    "maxResults": 10,
    "key": API_KEY,
}

DATA_DIR = Path(__file__).parent / "data"
CST = timezone(timedelta(hours=8))


def format_count(n) -> str:
    if n is None:
        return "—"
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fetch_youtube_trending(top_n: int = 10):
    if not API_KEY:
        raise RuntimeError("缺少 YOUTUBE_API_KEY 环境变量")

    print(f"📡  正在抓取 YouTube 热门视频 Top {top_n} (US)...")

    response = requests.get(URL, params=PARAMS, timeout=15)
    print(f"     HTTP 状态码：{response.status_code}")
    response.raise_for_status()

    data = response.json()
    items = data.get("items", [])

    if not items:
        raise RuntimeError("没拿到数据")

    now = datetime.now(CST)

    normalized = []
    for i, item in enumerate(items[:top_n], start=1):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        vid = item.get("id", "")

        view = stats.get("viewCount")
        like = stats.get("likeCount")
        comment = stats.get("commentCount")

        # 封面优先用 high，没有就 medium
        thumbnails = snippet.get("thumbnails", {})
        cover = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )

        normalized.append({
            "rank": i,
            "title": snippet.get("title", ""),
            "author": snippet.get("channelTitle", ""),
            "author_avatar": "",
            "view": int(view) if view else 0,
            "like": int(like) if like else 0,
            "reply": int(comment) if comment else 0,
            "share": 0,
            "view_text": format_count(view),
            "like_text": format_count(like),
            "reply_text": format_count(comment),
            "share_text": "—",
            "url": f"https://www.youtube.com/watch?v={vid}",
            "cover": cover,
            "bvid": vid,
            "published_at": snippet.get("publishedAt", ""),
            "category_id": snippet.get("categoryId", ""),
        })

    return {
        "platform": "youtube",
        "platform_name": "YouTube",
        "region": PARAMS["regionCode"],
        "fetched_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "videos": normalized,
    }


def save_to_json(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    latest_path = DATA_DIR / "youtube_latest.json"
    archive_path = DATA_DIR / f"youtube_{data['date']}.json"
    for path in [latest_path, archive_path]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾  已保存：{path.relative_to(Path(__file__).parent)}")


def print_preview(data: dict, top_n: int = 5):
    print(f"\n=== YouTube 热门 · {data['region']} · {data['date']} · 前 {top_n} 条 ===\n")
    for v in data["videos"][:top_n]:
        title = v["title"][:60] + ("..." if len(v["title"]) > 60 else "")
        print(f"#{v['rank']:>2}  {title}")
        print(f"     {v['author']}")
        print(f"     👁 {v['view_text']}  ❤ {v['like_text']}  💬 {v['reply_text']}")
        print(f"     🔗 {v['url']}")
        print()


if __name__ == "__main__":
    try:
        data = fetch_youtube_trending(top_n=10)
        save_to_json(data)
        print_preview(data, top_n=5)
        print(f"✅  完成！共抓取 {len(data['videos'])} 条")
    except Exception as e:
        print(f"⚠️ YouTube 抓取失败：{e}")
        raise SystemExit(0)
