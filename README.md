# Hot Feed Watch 🔥

每日多平台热门视频追踪与洞察工具。

## 功能

- 📊 抓取 B 站、抖音、TikTok、小红书每日热门 Top 10
- 🤖 AI 自动生成跨平台热点洞察
- 📅 历史数据归档，可按日期回看
- ⏰ 每日 20:00 自动更新

## 当前进度

- ✅ B 站热门榜抓取
- 🚧 抖音热门榜（开发中）
- 🚧 TikTok 热门榜（开发中）
- 🚧 小红书热点话题（开发中）

## 项目结构

\`\`\`
hot-feed-watch/
├── data/                    # 抓取到的 JSON 数据
├── fetch_bilibili.py        # B 站抓取脚本
├── requirements.txt         # Python 依赖
└── README.md
\`\`\`

## 在线 Demo

🌐 https://hot-feed-watch.lovable.app/

## Tech Stack

- 后端：Python 3.13 + requests
- 前端：React + Tailwind CSS（Lovable 生成）
- 数据托管：GitHub Raw
- 部署：Vercel via Lovable