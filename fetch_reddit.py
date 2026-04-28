"""
抓取 Reddit r/videos 当日 Top 10
"""
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Reddit 给开发者的"魔法":URL 后面加 .json 就直接吐 JSON
# t=day 表示"过去 24 小时", limit=15 多拿几条以防有 sticky/pinned
URL = "https://www.reddit.com/r/videos/top.json"
PARAMS = {"t": "day", "limit": 15}

HEADERS = {
    # Reddit 强制要求 User-Agent 不能是默认的, 否则给你 429
    # 格式建议: <platform>:<app-name>:<version> (by /u/<username>)
    "User-Agent": "macos:hot-feed-watch:0.1 (by /u/Maggie474747)",
    "Accept": "application/json",
}

DATA_DIR = Path(__file__).parent / "data"
CST = timezone(timedelta(hours=8))


def format_count(n: int) -> str:
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fetch_reddit_top(top_n: int = 10):
    """抓取 Reddit r/videos 当日 Top N"""
    print(f"📡  正在抓取 Reddit r/videos · 当日 Top {top_n}...")

    response = requests.get(URL, headers=HEADERS, params=PARAMS, timeout=15)
    print(f"     HTTP 状态码：{response.status_code}")
    response.raise_for_status()
    data = response.json()

    # Reddit API 结构: data.children 是帖子列表
    posts = data.get("data", {}).get("children", [])

    if not posts:
        raise RuntimeError("没拿到数据")

    now = datetime.now(CST)

    normalized = []
    rank = 0
    for child in posts:
        post = child.get("data", {})

        # 跳过版主置顶帖（不算热门）
        if post.get("stickied"):
            continue

        rank += 1
        if rank > top_n:
            break

        title = post.get("title", "")
        author = post.get("author", "unknown")
        ups = post.get("ups", 0)              # 赞数
        score = post.get("score", 0)          # 净分（赞-踩）
        comments = post.get("num_comments", 0)
        upvote_ratio = post.get("upvote_ratio", 0)  # 0~1
        permalink = post.get("permalink", "")
        url = f"https://www.reddit.com{permalink}"

        # 缩略图: Reddit 帖子的预览图（如果有）
        thumbnail = post.get("thumbnail", "")
        # Reddit thumbnail 有时候是 "self"/"default"/"nsfw" 这种特殊值, 不是真图
        if thumbnail in ("self", "default", "nsfw", "image", ""):
            # 试试从 preview 拿
            preview = post.get("preview", {}).get("images", [])
            if preview:
                source = preview[0].get("source", {})
                thumbnail = source.get("url", "").replace("&amp;", "&")
            else:
                thumbnail = ""

        normalized.append({
            "rank": rank,
            "title": title,
            "author": f"u/{author}",
            "author_avatar": "",
            "view": ups,
            "like": ups,
            "reply": comments,
            "share": 0,
            "view_text": format_count(ups) + " upvotes",
            "like_text": f"{int(upvote_ratio * 100)}%" if upvote_ratio else "—",
            "reply_text": format_count(comments),
            "share_text": post.get("link_flair_text") or "—",
            "url": url,
            "cover": thumbnail,
            "bvid": post.get("id", ""),
            "score": score,
        })

    return {
        "platform": "reddit",
        "platform_name": "Reddit",
        "subreddit": "r/videos",
        "fetched_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "videos": normalized,
    }


def save_to_json(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    latest_path = DATA_DIR / "reddit_latest.json"
    archive_path = DATA_DIR / f"reddit_{data['date']}.json"
    for path in [latest_path, archive_path]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾  已保存：{path.relative_to(Path(__file__).parent)}")


def print_preview(data: dict, top_n: int = 5):
    print(f"\n=== Reddit r/videos · {data['date']} · 前 {top_n} 条 ===\n")
    for v in data["videos"][:top_n]:
        # 标题太长截断, 终端美观
        title = v['title']
        if len(title) > 70:
            title = title[:67] + "..."
        print(f"#{v['rank']:>2}  {title}")
        print(f"     {v['author']}")
        print(f"     ⬆ {v['view_text']}  💬 {v['reply_text']}  📊 {v['like_text']}")
        print(f"     🔗 {v['url']}")
        print()


if __name__ == "__main__":
    data = fetch_reddit_top(top_n=10)
    save_to_json(data)
    print_preview(data, top_n=5)
    print(f"✅  完成！共抓取 {len(data['videos'])} 条")