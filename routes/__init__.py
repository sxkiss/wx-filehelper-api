"""
Routes package - 模块化路由

核心路由:
- bot: Telegram Bot API 兼容
- wechat: 微信扩展接口
- files: 文件管理接口

框架管理路由已移至插件: plugins/framework_api.py
"""

from .bot import router as bot_router
from .wechat import router as wechat_router
from .files import router as files_router

__all__ = ["bot_router", "wechat_router", "files_router"]
