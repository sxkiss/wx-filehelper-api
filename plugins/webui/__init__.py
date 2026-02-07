"""
WebUI 插件 - 提供 Web 管理界面

功能:
- 登录二维码展示 (自适应窗口)
- 登录状态实时刷新
- 服务器状态监控
- 消息/文件发送

路由:
- GET /webui - 主页面
- GET /webui/qr - 二维码 (Base64 JSON)
- GET /webui/status - 状态 JSON

可通过删除此文件夹禁用 WebUI。
"""

import base64
import time
from pathlib import Path
from typing import Any

from fastapi.responses import HTMLResponse

from plugin_base import route, get_bot, get_processor, get_config


# 插件目录路径
PLUGIN_DIR = Path(__file__).parent


# === API 路由 ===


@route("GET", "/webui/qr", tags=["WebUI"])
async def webui_qr() -> dict[str, Any]:
    """获取二维码 (Base64 编码, 快速响应)"""
    bot = get_bot()

    # 快速检查: 仅检查内存状态，不做网络请求
    if bot._has_auth() and bot.is_logged_in:
        return {
            "logged_in": True,
            "qr_base64": None,
            "message": "已登录",
        }

    try:
        # 使用 skip_login_check=True 避免重复检查
        png_bytes = await bot.get_login_qr(skip_login_check=True)
        if not png_bytes:
            return {
                "logged_in": True,
                "qr_base64": None,
                "message": "已登录",
            }

        qr_base64 = base64.b64encode(png_bytes).decode("ascii")
        return {
            "logged_in": False,
            "qr_base64": qr_base64,
            "uuid": bot.uuid,
            "uuid_age": int(time.time() - bot.uuid_ts) if bot.uuid_ts else 0,
            "message": "请扫码登录",
        }
    except Exception as exc:
        return {
            "logged_in": False,
            "qr_base64": None,
            "error": str(exc),
            "message": f"获取二维码失败: {exc}",
        }


@route("GET", "/webui/status", tags=["WebUI"])
async def webui_status(poll_login: bool = False) -> dict[str, Any]:
    """
    获取服务器状态

    Args:
        poll_login: 是否主动轮询登录状态 (未登录时自动触发)
    """
    bot = get_bot()
    processor = get_processor()
    config = get_config()

    # 未登录时自动触发登录轮询
    if poll_login or not bot.is_logged_in:
        await bot.check_login_status(poll=True)

    # 获取登录状态详情
    login_detail = await bot.get_login_status_detail()

    uptime = int(time.time() - processor.started_at)

    return {
        "app_name": config.app_name,
        "version": config.version,
        "uptime": uptime,
        "uptime_str": _format_uptime(uptime),
        "logged_in": login_detail.get("logged_in", False),
        "login_status": login_detail.get("status", "unknown"),
        "login_code": login_detail.get("code", 0),
        "has_uuid": login_detail.get("has_uuid", False),
        "uuid_age": login_detail.get("uuid_age_seconds"),
        "chat_enabled": processor.chat_enabled,
        "tasks_count": len(processor.tasks),
        "plugins_count": len(processor.plugin_loader.loaded_plugins),
        "entry_host": login_detail.get("entry_host", ""),
        "login_status_text": _get_login_status_text(login_detail),
    }


@route("GET", "/webui", tags=["WebUI"])
async def webui_page() -> HTMLResponse:
    """WebUI 主页面"""
    config = get_config()
    html = _load_html(config.app_name, config.version)
    return HTMLResponse(content=html, status_code=200)


# === 辅助函数 ===


def _format_uptime(seconds: int) -> str:
    """格式化运行时间"""
    if seconds < 60:
        return f"{seconds}秒"
    if seconds < 3600:
        return f"{seconds // 60}分{seconds % 60}秒"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}小时{minutes}分"


def _get_login_status_text(login_detail: dict) -> str:
    """根据登录状态返回中文描述"""
    if login_detail.get("logged_in"):
        return "已登录"

    code = login_detail.get("code", 0)
    status = login_detail.get("status", "")

    if code == 201:
        return "已扫码，请在手机上确认"
    if code == 408:
        return "等待扫码..."
    if status == "qr_expired":
        return "二维码已过期，请刷新"
    if status == "need_qr":
        return "请扫描二维码"
    if status == "qr_ready":
        return "二维码已就绪"

    return "等待登录"


def _load_html(app_name: str, version: str) -> str:
    """从文件加载 HTML 模板并替换变量"""
    html_path = PLUGIN_DIR / "index.html"

    if not html_path.exists():
        return f"<h1>Error: index.html not found in {PLUGIN_DIR}</h1>"

    html = html_path.read_text(encoding="utf-8")

    # 简单的模板变量替换
    html = html.replace("{{app_name}}", app_name)
    html = html.replace("{{version}}", version)

    return html
