"""
WeChat 扩展路由

微信特有功能，Telegram 无对应接口
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Query, Response, HTTPException

if TYPE_CHECKING:
    from direct_bot import WeChatHelperBot

router = APIRouter(prefix="/wechat", tags=["WeChat Extensions"])

# 依赖注入
_bot: "WeChatHelperBot | None" = None


def init(bot: "WeChatHelperBot"):
    """初始化路由依赖"""
    global _bot
    _bot = bot


def _get_bot() -> "WeChatHelperBot":
    if _bot is None:
        raise RuntimeError("Bot not initialized")
    return _bot


# 注: 登录相关路由已统一到根路径
# - GET /qr -> 获取二维码
# - GET /login/status -> 登录状态
# - GET /webui -> Web 管理界面


@router.post("/session/save")
async def save_session() -> dict[str, bool]:
    """保存会话"""
    bot = _get_bot()
    success = await bot.save_session()
    return {"ok": success}


@router.get("/trace/status")
async def trace_status() -> dict[str, Any]:
    """Trace 状态"""
    bot = _get_bot()
    return bot.get_trace_status()


@router.get("/trace/recent")
async def trace_recent(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    """最近的 Trace 记录"""
    bot = _get_bot()
    rows = await bot.read_recent_traces(limit=limit)
    return {"count": len(rows), "rows": rows}


@router.post("/trace/clear")
async def trace_clear() -> dict[str, str]:
    """清除 Trace 日志"""
    bot = _get_bot()
    await bot.clear_traces()
    return {"status": "cleared"}
