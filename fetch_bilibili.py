"""
抓取 B 站热门视频榜 Top 10，并保存为 JSON 文件
"""
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# B 站公开 API：popular 接口
URL = "https://api.bilibili.com/x/web-interface/popular"

# 模拟浏览器，避免被当成爬虫拒绝
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

# 输出目录：项目根目录下的 data/ 文件夹
DATA_DIR = Path(__file__).parent / "data"

# 北京时间（UTC+8）
CST = timezone(timedelta(hours=8))


def format_count(n: int) -> str:
    """把数字格式化成中文友好的形式：1.2万、3.4亿"""
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return str(n)


def fetch_bilibili_popular(top_n: int = 10):
    """抓取 B 站热门榜前 N 条，返回标准化的字典"""
    print(f"📡  正在抓取 B 站热门榜 Top {top_n}...")

    response = requests.get(URL, headers=HEADERS, params={"ps": top_n}, timeout=10)
    response.raise_for_status()
    data = response.json()
    videos = data.get("data", {}).get("list", [])

    if not videos:
        raise RuntimeError("没拿到数据，可能接口变了或被限流")

    now = datetime.now(CST)

    # 把 B 站原始数据，转成我们前端要用的标准结构
    normalized = []
    for i, v in enumerate(videos[:top_n], start=1):
        stat = v.get("stat", {})
        view = stat.get("view", 0)
        like = stat.get("like", 0)
        reply = stat.get("reply", 0)
        share = stat.get("share", 0)
        bvid = v.get("bvid", "")

        normalized.append({
            "rank": i,
            "title": v.get("title", "无标题"),
            "author": v.get("owner", {}).get("name", "未知作者"),
            "author_avatar": v.get("owner", {}).get("face", ""),
            "view": view,
            "like": like,
            "reply": reply,
            "share": share,
            "view_text": format_count(view),
            "like_text": format_count(like),
            "reply_text": format_count(reply),
            "share_text": format_count(share),
            "url": f"https://www.bilibili.com/video/{bvid}",
            "cover": v.get("pic", ""),
            "bvid": bvid,
        })

    return {
        "platform": "bilibili",
        "platform_name": "B站",
        "fetched_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "videos": normalized,
    }


def save_to_json(data: dict):
    """把数据保存成两份 JSON：
    1. data/bilibili_latest.json —— 最新一份（前端读这个）
    2. data/bilibili_2026-04-28.json —— 当日存档（按日期归档，便于历史回看）
    """
    DATA_DIR.mkdir(exist_ok=True)

    latest_path = DATA_DIR / "bilibili_latest.json"
    archive_path = DATA_DIR / f"bilibili_{data['date']}.json"

    for path in [latest_path, archive_path]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾  已保存：{path.relative_to(Path(__file__).parent)}")


def print_preview(data: dict, top_n: int = 5):
    """打印前 N 条预览，让人眼能确认数据对不对"""
    print(f"\n=== B 站热门榜 · {data['date']} · 前 {top_n} 条预览 ===\n")
    for v in data["videos"][:top_n]:
        print(f"#{v['rank']:>2}  {v['title']}")
        print(f"     UP主：{v['author']}")
        print(f"     👁 {v['view_text']}  ❤ {v['like_text']}  💬 {v['reply_text']}  🔁 {v['share_text']}")
        print(f"     🔗 {v['url']}")
        print()


if __name__ == "__main__":
    data = fetch_bilibili_popular(top_n=10)
    save_to_json(data)
    print_preview(data, top_n=5)
    print(f"✅  完成！共抓取 {len(data['videos'])} 条")