"""
抓取 Reddit r/videos 当日 Top 10
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Reddit 给开发者的 "魔法": URL 后面加 .json 就直接吐 JSON
# t=day 表示 "过去 24 小时", limit=15 多拿几条以防有 sticky/pinned
URL = "https://www.reddit.com/r/videos/top.json"
PARAMS = {"t": "day", "limit": 15}

HEADERS = {
    # 格式建议: <platform>:<app-name>:<version> (by /u/<username>)
    "User-Agent": "macos:hot-feed-watch:0.1 (by /u/Maggie474747)",
    "Accept": "application/json",
}

# 带重试的会话，提升 GitHub Actions 环境稳定性
SESSION = requests.Session()
RETRY = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    raise_on_status=False,
)
SESSION.mount("https://", HTTPAdapter(max_retries=RETRY))
SESSION.mount("http://", HTTPAdapter(max_retries=RETRY))

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

    response = SESSION.get(URL, headers=HEADERS, params=PARAMS, timeout=20)
    print(f"     HTTP 状态码：{response.status_code}")

    if response.status_code == 403:
        raise RuntimeError("Reddit 返回 403（可能触发反爬策略）")
    if response.status_code == 429:
        raise RuntimeError("Reddit 返回 429（请求过于频繁）")

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
        ups = post.get("ups", 0)  # 赞数
        score = post.get("score", 0)  # 净分（赞-踩）
        comments = post.get("num_comments", 0)
        upvote_ratio = post.get("upvote_ratio", 0)  # 0~1
        permalink = post.get("permalink", "")
        url = f"https://www.reddit.com{permalink}"

        # 缩略图：按可靠性优先级尝试多个来源
        thumbnail = ""

        # 优先级 1：post 自带的 media oembed thumbnail（最稳，多为 YouTube/外站官方缩略图）
        media = post.get("media") or {}
        oembed = media.get("oembed") or {}
        if oembed.get("thumbnail_url"):
            thumbnail = oembed["thumbnail_url"]

        # 优先级 2：preview.images[0].source.url（Reddit 自己的缩略图）
        if not thumbnail:
            preview = post.get("preview", {}).get("images", [])
            if preview:
                source = preview[0].get("source", {})
                thumbnail = source.get("url", "")

        # 优先级 3：post.thumbnail（最不稳定，但作为兜底）
        if not thumbnail:
            tn = post.get("thumbnail", "")
            if tn not in ("self", "default", "nsfw", "image", "spoiler", ""):
                thumbnail = tn

        # HTML 实体解码（Reddit API 返回的 URL 里 & 被转义成 &amp;）
        if thumbnail:
            thumbnail = thumbnail.replace("&amp;", "&")

        normalized.append(
            {
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
            }
        )

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
        title = v["title"]
        if len(title) > 70:
            title = title[:67] + "..."
        print(f"#{v['rank']:>2}  {title}")
        print(f"     {v['author']}")
        print(f"     ⬆ {v['view_text']}  💬 {v['reply_text']}  📊 {v['like_text']}")
        print(f"     🔗 {v['url']}")
        print()


if __name__ == "__main__":
    try:
        data = fetch_reddit_top(top_n=10)
        save_to_json(data)
        print_preview(data, top_n=5)
        print(f"✅  完成！共抓取 {len(data['videos'])} 条")
    except Exception as e:
        print(f"⚠️ Reddit 抓取失败：{e}")
        # 关键：退出 0，避免影响其它平台定时任务
        raise SystemExit(0)