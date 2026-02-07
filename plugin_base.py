"""
插件基础模块 - 提供插件开发所需的基类和装饰器

开发者只需:
1. 在 plugins/ 目录创建 .py 文件
2. 使用 @command 装饰器注册命令
3. 使用 @on_message 装饰器处理消息
4. 使用 @route 装饰器注册 HTTP 路由
5. 使用 @on_load/@on_unload 处理生命周期

示例:
    from plugin_base import command, on_message, route, on_load, CommandContext
    from plugin_base import get_bot, get_processor, get_config

    @on_load
    async def init():
        print("插件已加载")

    @command("hello", description="打招呼")
    async def hello_cmd(ctx: CommandContext) -> str:
        return f"你好, {ctx.args[0] if ctx.args else '世界'}!"

    @on_message(priority=10)
    async def log_all(ctx: CommandContext) -> str | None:
        print(f"收到消息: {ctx.text}")
        return None  # 返回 None 表示不拦截

    @route("GET", "/my-plugin/status")
    async def my_status():
        return {"status": "ok"}
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
import functools


# === 全局依赖 (运行时注入) ===

_bot: Any = None
_processor: Any = None
_config: Any = None


def inject_dependencies(bot: Any, processor: Any, config: Any) -> None:
    """注入全局依赖 (由框架调用)"""
    global _bot, _processor, _config
    _bot = bot
    _processor = processor
    _config = config


def get_bot():
    """获取 WeChatHelperBot 实例"""
    if _bot is None:
        # 兼容旧方式
        from main import wechat_bot
        return wechat_bot
    return _bot


def get_processor():
    """获取 CommandProcessor 实例"""
    if _processor is None:
        from main import command_processor
        return command_processor
    return _processor


def get_config():
    """获取配置实例"""
    if _config is None:
        from config import settings
        return settings
    return _config


# === 数据类 ===


@dataclass
class CommandContext:
    """命令执行上下文"""
    text: str                          # 原始文本
    command: str                       # 命令名 (不含 /)
    args: list[str]                    # 参数列表
    msg: dict[str, Any]                # 原始消息对象
    msg_id: str                        # 消息ID
    is_command: bool                   # 是否为命令调用
    bot: Any = None                    # WeChatHelperBot 实例
    processor: Any = None              # CommandProcessor 实例
    reply_to: str | None = None        # 回复的消息ID (如果有)
    extra: dict[str, Any] = field(default_factory=dict)  # 扩展数据


CommandHandler = Callable[[CommandContext], Awaitable[str | None]]
MessageHandler = Callable[[CommandContext], Awaitable[str | None]]
RouteHandler = Callable[..., Awaitable[Any]]


@dataclass
class CommandInfo:
    """命令注册信息"""
    name: str
    handler: CommandHandler
    description: str = ""
    usage: str = ""
    aliases: list[str] = field(default_factory=list)
    hidden: bool = False


@dataclass
class MessageHandlerInfo:
    """消息处理器注册信息"""
    handler: MessageHandler
    priority: int = 0
    name: str = ""


@dataclass
class RouteInfo:
    """路由注册信息"""
    method: str              # GET, POST, PUT, DELETE, PATCH
    path: str                # URL 路径
    handler: RouteHandler    # 处理函数
    name: str = ""           # 路由名称
    tags: list[str] = field(default_factory=list)  # OpenAPI 标签


LifecycleHandler = Callable[[], Awaitable[None]]


# 全局注册表 - 插件加载时自动填充
_commands: dict[str, CommandInfo] = {}
_message_handlers: list[MessageHandlerInfo] = []
_routes: list[RouteInfo] = []
_on_load_handlers: list[LifecycleHandler] = []
_on_unload_handlers: list[LifecycleHandler] = []
_handlers_sorted: bool = True  # 标记是否已排序


def command(
    name: str,
    description: str = "",
    usage: str = "",
    aliases: list[str] | None = None,
    hidden: bool = False,
):
    """
    命令装饰器 - 注册一个命令处理函数

    Args:
        name: 命令名称 (不含 /)
        description: 命令描述 (用于 /help)
        usage: 使用说明
        aliases: 命令别名列表
        hidden: 是否在 help 中隐藏

    Example:
        @command("ping", description="测试连通性")
        async def ping_cmd(ctx: CommandContext) -> str:
            return "pong"
    """
    def decorator(func: CommandHandler) -> CommandHandler:
        info = CommandInfo(
            name=name.lower(),
            handler=func,
            description=description,
            usage=usage or f"/{name}",
            aliases=aliases or [],
            hidden=hidden,
        )
        _commands[name.lower()] = info
        for alias in info.aliases:
            _commands[alias.lower()] = info

        @functools.wraps(func)
        async def wrapper(ctx: CommandContext) -> str | None:
            return await func(ctx)
        return wrapper

    return decorator


def on_message(priority: int = 0, name: str = ""):
    """
    消息处理器装饰器 - 注册一个消息处理函数

    处理器按 priority 降序执行，返回非 None 时停止后续处理器

    Args:
        priority: 优先级 (越大越先执行)
        name: 处理器名称 (用于调试)

    Example:
        @on_message(priority=100)
        async def filter_spam(ctx: CommandContext) -> str | None:
            if "广告" in ctx.text:
                return "检测到垃圾消息，已忽略"
            return None  # 继续后续处理
    """
    global _handlers_sorted

    def decorator(func: MessageHandler) -> MessageHandler:
        info = MessageHandlerInfo(
            handler=func,
            priority=priority,
            name=name or func.__name__,
        )
        _message_handlers.append(info)
        _handlers_sorted = False  # 标记需要重新排序

        @functools.wraps(func)
        async def wrapper(ctx: CommandContext) -> str | None:
            return await func(ctx)
        return wrapper

    return decorator


def route(
    method: str,
    path: str,
    name: str = "",
    tags: list[str] | None = None,
):
    """
    路由装饰器 - 注册一个 HTTP 路由

    Args:
        method: HTTP 方法 (GET, POST, PUT, DELETE, PATCH)
        path: URL 路径
        name: 路由名称 (用于调试)
        tags: OpenAPI 标签

    Example:
        @route("GET", "/my-plugin/status", tags=["MyPlugin"])
        async def my_status():
            return {"status": "ok", "plugin": "my-plugin"}

        @route("POST", "/my-plugin/action")
        async def my_action(data: dict):
            return {"result": "done"}
    """
    def decorator(func: RouteHandler) -> RouteHandler:
        info = RouteInfo(
            method=method.upper(),
            path=path,
            handler=func,
            name=name or func.__name__,
            tags=tags or [],
        )
        _routes.append(info)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper

    return decorator


def on_load(func: LifecycleHandler) -> LifecycleHandler:
    """
    插件加载钩子 - 插件加载完成后执行

    Example:
        @on_load
        async def init():
            print("插件已加载")
            # 初始化资源、连接数据库等
    """
    _on_load_handlers.append(func)

    @functools.wraps(func)
    async def wrapper():
        return await func()
    return wrapper


def on_unload(func: LifecycleHandler) -> LifecycleHandler:
    """
    插件卸载钩子 - 插件卸载前执行

    Example:
        @on_unload
        async def cleanup():
            print("插件即将卸载")
            # 清理资源、关闭连接等
    """
    _on_unload_handlers.append(func)

    @functools.wraps(func)
    async def wrapper():
        return await func()
    return wrapper


def get_registered_commands() -> dict[str, CommandInfo]:
    """获取所有已注册的命令 (直接返回，无复制)"""
    return _commands


def get_message_handlers() -> list[MessageHandlerInfo]:
    """获取所有消息处理器 (按优先级排序，延迟排序)"""
    global _handlers_sorted
    if not _handlers_sorted:
        _message_handlers.sort(key=lambda x: -x.priority)
        _handlers_sorted = True
    return _message_handlers


def get_registered_routes() -> list[RouteInfo]:
    """获取所有已注册的路由"""
    return _routes


def clear_registry():
    """清空注册表 (用于测试或重新加载)"""
    global _handlers_sorted
    _commands.clear()
    _message_handlers.clear()
    _routes.clear()
    _on_load_handlers.clear()
    _on_unload_handlers.clear()
    _handlers_sorted = True


def get_lifecycle_handlers() -> tuple[list[LifecycleHandler], list[LifecycleHandler]]:
    """获取生命周期钩子 (on_load, on_unload)"""
    return _on_load_handlers, _on_unload_handlers


async def run_on_load_handlers() -> None:
    """执行所有 on_load 钩子"""
    for handler in _on_load_handlers:
        try:
            await handler()
        except Exception as exc:
            print(f"[PluginBase] on_load error: {exc}")


async def run_on_unload_handlers() -> None:
    """执行所有 on_unload 钩子"""
    for handler in _on_unload_handlers:
        try:
            await handler()
        except Exception as exc:
            print(f"[PluginBase] on_unload error: {exc}")


def get_help_text() -> str:
    """生成帮助文本"""
    lines = ["可用命令:"]
    seen = set()
    for info in _commands.values():
        if info.hidden or info.name in seen:
            continue
        seen.add(info.name)
        desc = f" - {info.description}" if info.description else ""
        aliases = f" (别名: {', '.join(info.aliases)})" if info.aliases else ""
        lines.append(f"  /{info.name}{desc}{aliases}")
    return "\n".join(lines)
