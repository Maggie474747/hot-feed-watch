"""
抓取 TikTok Creative Center 热门话题榜（新加坡地区，最近 7 天）
"""
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# TikTok Creative Center 的内部 API
# country_code 可改地区: SG=新加坡, US=美国, ID=印尼, RU=俄罗斯, AE=阿联酋
URL = "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list"

PARAMS = {
    "page": 1,
    "limit": 10,           # 拿前 10 个
    "period": 7,           # 最近 7 天
    "country_code": "SG",  # 新加坡
    "sort_by": "popular",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://ads.tiktok.com",
}

DATA_DIR = Path(__file__).parent / "data"
CST = timezone(timedelta(hours=8))


def format_count(n: int) -> str:
    """1234567 → 1.2M / 12345 → 12.3K"""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fetch_tiktok_hashtags(top_n: int = 10):
    """抓取 TikTok 热门话题"""
    print(f"📡  正在抓取 TikTok Creative Center 热门话题 Top {top_n} ({PARAMS['country_code']}, 近 {PARAMS['period']} 天)...")

    response = requests.get(URL, headers=HEADERS, params=PARAMS, timeout=15)
    print(f"     HTTP 状态码：{response.status_code}")

    if response.status_code != 200:
        print(f"\n⚠️  请求失败，响应内容预览：\n{response.text[:500]}")
        raise RuntimeError(f"HTTP {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(f"\n⚠️  返回不是 JSON，预览：\n{response.text[:500]}")
        raise

    # TikTok API 的固定结构：data.data.list
    items = data.get("data", {}).get("list", [])

    if not items:
        print(f"\n⚠️  没拿到数据，完整返回：\n{json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
        raise RuntimeError("空数据")

    now = datetime.now(CST)

    normalized = []
    for i, h in enumerate(items[:top_n], start=1):
        name = h.get("hashtag_name", "")
        post_count = h.get("publish_cnt", 0)
        view_count = h.get("video_views", 0) or h.get("view_cnt", 0)
        rank_diff = h.get("rank_diff", 0)
        is_new = h.get("trend") == 1 or rank_diff is None

        normalized.append({
            "rank": i,
            "title": f"#{name}",
            "author": h.get("industry_value", "TikTok Trending"),
            "author_avatar": "",
            "view": view_count,
            "like": 0,
            "reply": 0,
            "share": post_count,  # 用 post_count 占位 share 字段
            "view_text": format_count(view_count) if view_count else "—",
            "like_text": "—",
            "reply_text": "—",
            "share_text": f"{format_count(post_count)} posts",
            "url": f"https://www.tiktok.com/tag/{name}",
            "cover": "",
            "bvid": name,
            "is_new": is_new,
            "rank_diff": rank_diff,
        })

    return {
        "platform": "tiktok",
        "platform_name": "TikTok",
        "region": PARAMS["country_code"],
        "period_days": PARAMS["period"],
        "fetched_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "videos": normalized,
    }


def save_to_json(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    latest_path = DATA_DIR / "tiktok_latest.json"
    archive_path = DATA_DIR / f"tiktok_{data['date']}.json"
    for path in [latest_path, archive_path]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾  已保存：{path.relative_to(Path(__file__).parent)}")


def print_preview(data: dict, top_n: int = 5):
    print(f"\n=== TikTok 热门话题 · {data['region']} · 近 {data['period_days']} 天 · 前 {top_n} 条 ===\n")
    for v in data["videos"][:top_n]:
        flag = "🆕" if v["is_new"] else (f"↑{v['rank_diff']}" if v["rank_diff"] else "")
        print(f"#{v['rank']:>2}  {v['title']}  {flag}")
        print(f"     行业：{v['author']}")
        print(f"     📹 {v['share_text']}   👁 {v['view_text']}")
        print(f"     🔗 {v['url']}")
        print()


if __name__ == "__main__":
    data = fetch_tiktok_hashtags(top_n=10)
    save_to_json(data)
    print_preview(data, top_n=5)
    print(f"✅  完成！共抓取 {len(data['videos'])} 条")