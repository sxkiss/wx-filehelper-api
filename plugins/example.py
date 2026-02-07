"""
示例插件 - 展示如何开发自定义命令、消息处理器和 HTTP 路由

这个文件可以作为插件开发的模板。
将 .py 文件放入 plugins/ 目录即可自动加载。
"""

from plugin_base import (
    command,
    on_message,
    route,
    on_load,
    on_unload,
    CommandContext,
    get_bot,
    get_processor,
    get_config,
)


# === 生命周期钩子 ===


@on_load
async def plugin_init():
    """插件加载时执行"""
    print("[ExamplePlugin] 插件已加载")
    # 可以在这里初始化资源，如数据库连接


@on_unload
async def plugin_cleanup():
    """插件卸载时执行"""
    print("[ExamplePlugin] 插件即将卸载")
    # 可以在这里清理资源


# === 自定义命令示例 ===


@command("time", description="显示当前时间", aliases=["now", "date"])
async def cmd_time(ctx: CommandContext) -> str:
    """显示当前服务器时间"""
    from datetime import datetime
    now = datetime.now()
    return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"


@command("calc", description="简单计算器", usage="/calc 1+2*3")
async def cmd_calc(ctx: CommandContext) -> str:
    """
    简单计算器 (仅支持基础运算)

    示例: /calc 1+2*3
    """
    if not ctx.args:
        return "用法: /calc 表达式\n示例: /calc 1+2*3"

    expr = " ".join(ctx.args)

    # 安全检查: 只允许数字和基础运算符
    import re
    if not re.match(r'^[\d\s\+\-\*\/\.\(\)]+$', expr):
        return "只支持数字和 + - * / ( ) 运算"

    try:
        # 使用 eval 但限制为纯数学表达式
        result = eval(expr, {"__builtins__": {}}, {})
        return f"{expr} = {result}"
    except Exception as exc:
        return f"计算错误: {exc}"


@command("uuid", description="生成 UUID")
async def cmd_uuid(ctx: CommandContext) -> str:
    """生成一个随机 UUID"""
    import uuid
    return str(uuid.uuid4())


@command("ip", description="查询服务器IP")
async def cmd_ip(ctx: CommandContext) -> str:
    """显示服务器的网络信息"""
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "unknown"

    return f"hostname={hostname}\nlocal_ip={local_ip}"


# === HTTP 路由示例 ===


@route("GET", "/example/status", tags=["Example"])
async def example_status():
    """示例插件状态"""
    config = get_config()
    return {
        "plugin": "example",
        "status": "running",
        "server_label": config.server_label,
    }


@route("GET", "/example/commands", tags=["Example"])
async def example_commands():
    """列出本插件提供的命令"""
    return {
        "commands": ["time", "calc", "uuid", "ip"],
        "aliases": {
            "time": ["now", "date"],
        },
    }


@route("POST", "/example/echo", tags=["Example"])
async def example_echo(text: str = ""):
    """回显接口 - 测试用"""
    return {"echo": text, "length": len(text)}


# === 消息处理器示例 ===


# @on_message(priority=100, name="spam_filter")
# async def filter_spam(ctx: CommandContext) -> str | None:
#     """
#     垃圾消息过滤器 (示例，默认禁用)
#
#     返回字符串会终止后续处理并回复该内容
#     返回 None 会继续后续处理
#     """
#     spam_keywords = ["广告", "优惠", "免费领取"]
#     for keyword in spam_keywords:
#         if keyword in ctx.text:
#             return f"检测到垃圾消息关键词: {keyword}"
#     return None


# @on_message(priority=50, name="auto_reply")
# async def auto_reply(ctx: CommandContext) -> str | None:
#     """
#     自动回复 (示例，默认禁用)
#     """
#     auto_replies = {
#         "在吗": "我在，有什么可以帮你的？",
#         "谢谢": "不客气！",
#     }
#     for trigger, reply in auto_replies.items():
#         if trigger in ctx.text:
#             return reply
#     return None
