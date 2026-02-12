<!-- AUTO-DOC: Update me when files in this folder change -->

# routes

FastAPI 路由层：提供 Telegram Bot API 兼容接口、微信扩展接口与文件管理接口。

## Files

| File | Role | Function |
|------|------|----------|
| `__init__.py` | Package | 导出路由实例（router） |
| `bot.py` | API | Telegram Bot API 兼容路由（sendMessage/getUpdates 等） |
| `wechat.py` | API | 微信扩展能力（登录、会话等） |
| `files.py` | API | 下载目录与文件元数据管理接口 |
