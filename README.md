# WeChat FileHelper Protocol Bot v2.0

一个**纯协议**（无浏览器自动化）微信文件传输助手机器人框架。
目标是把你的微信「文件传输助手」变成服务器控制台：可收发文本/文件、执行指令、回传服务器状态、接入聊天助手、定时任务自动执行。

## v2.0 新特性

- **插件化命令系统** - `plugins/` 目录自动加载，开发者只需创建文件即可扩展
- **消息持久化** - SQLite 存储历史消息，支持消息 ID 查询和分页
- **Telegram Bot API 兼容** - `getUpdates`、`sendMessage`、`sendDocument` 等接口
- **回复消息功能** - 支持 `reply_to_message_id` 参数
- **文件管理增强** - 按日期目录存储、元数据管理、自动清理
- **稳定性增强** - 心跳监控、自动重连、协议重试

## 设计目标

- 纯协议交互（`mmwebwx-bin`），不依赖 Playwright/Selenium
- 可扩展插件框架（命令、消息处理器、任务调度）
- 可观测性（协议抓包 trace、登录状态机、会话持久化）
- Telegram Bot API 兼容，便于迁移和集成
- 适配自有服务器交互（HTTP 调用、Webhook 对接）

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

服务默认监听：`http://127.0.0.1:8000`

## 登录流程

1. 访问 `GET /qr` 获取二维码
2. 手机微信扫码确认
3. 轮询 `GET /login/status`
   - `408`: 等待扫码
   - `201`: 已扫码待确认
   - `200`: 登录成功

## API 概览

### 基础 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务状态总览 |
| `/qr` | GET | 登录二维码 |
| `/login/status` | GET | 登录状态 |
| `/send` | POST | 发送文本 |
| `/upload` | POST | 发送文件 |
| `/messages` | GET | 最近消息 |
| `/health` | GET | 健康检查 |

### Telegram Bot API 兼容

| 端点 | 方法 | 说明 |
|------|------|------|
| `/bot/getUpdates` | GET | 获取消息更新 (支持 offset 分页) |
| `/bot/sendMessage` | POST | 发送消息 (支持 reply_to_message_id) |
| `/bot/sendDocument` | POST | 发送文件 |
| `/bot/getMe` | GET | 获取机器人信息 |
| `/bot/getMessage` | GET | 按 ID 查询消息 |

**示例：获取新消息**

```bash
# 首次获取
curl "http://127.0.0.1:8000/bot/getUpdates?limit=10"

# 获取 offset 之后的消息 (用于分页)
curl "http://127.0.0.1:8000/bot/getUpdates?offset=100&limit=10"
```

**示例：发送消息并回复**

```bash
curl -X POST http://127.0.0.1:8000/bot/sendMessage \
  -H "Content-Type: application/json" \
  -d '{"text":"回复内容","reply_to_message_id":"1234567890"}'
```

### 消息存储 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/store/stats` | GET | 存储统计 |
| `/store/messages` | GET | 查询历史消息 |

### 文件管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/downloads` | GET | 文件列表 (支持子目录) |
| `/files/metadata` | GET | 文件元数据 |
| `/files/{msg_id}` | DELETE | 删除文件 |
| `/files/cleanup` | POST | 清理过期文件 |

### 插件 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/plugins` | GET | 列出已加载插件 |
| `/plugins/reload` | POST | 重新加载插件 |

### Framework API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/framework/state` | GET | 框架状态 |
| `/framework/execute` | POST | 执行命令 |
| `/framework/tasks` | GET/POST | 定时任务管理 |
| `/framework/chat_mode` | POST | 聊天模式开关 |

### 稳定性 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/stability` | GET | 稳定性状态 (重连次数、心跳等) |

## 插件开发

### 创建命令

在 `plugins/` 目录创建 `.py` 文件：

```python
# plugins/my_plugin.py
from plugin_base import command, CommandContext

@command("hello", description="打招呼", aliases=["hi"])
async def cmd_hello(ctx: CommandContext) -> str:
    name = ctx.args[0] if ctx.args else "世界"
    return f"你好, {name}!"
```

重启服务或调用 `POST /plugins/reload` 即可生效。

### 命令装饰器参数

```python
@command(
    name="mycmd",           # 命令名
    description="说明",     # /help 中显示
    usage="/mycmd <arg>",   # 使用说明
    aliases=["mc", "m"],    # 别名
    hidden=False,           # 是否隐藏
)
```

### CommandContext 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `text` | str | 原始消息文本 |
| `command` | str | 命令名 |
| `args` | list[str] | 参数列表 |
| `msg` | dict | 原始消息对象 |
| `msg_id` | str | 消息 ID |
| `is_command` | bool | 是否为 `/` 开头的命令 |
| `bot` | WeChatHelperBot | 机器人实例 |
| `processor` | CommandProcessor | 处理器实例 |
| `reply_to` | str \| None | 回复的消息 ID |

### 消息处理器

```python
from plugin_base import on_message, CommandContext

@on_message(priority=100, name="my_filter")
async def my_handler(ctx: CommandContext) -> str | None:
    # 返回字符串: 回复该内容并停止后续处理
    # 返回 None: 继续后续处理
    if "关键词" in ctx.text:
        return "检测到关键词"
    return None
```

## 微信侧命令

发送给文件传输助手：

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助 |
| `/status` | 服务器状态 |
| `/plugins` | 插件状态 |
| `/chat on\|off` | 聊天模式 |
| `/ask 问题` | 聊天问答 |
| `/httpget URL` | HTTP 请求 |
| `/sendfile 文件名` | 发送文件 |
| `/task list\|add\|del\|run` | 定时任务 |
| `/time` | 当前时间 |
| `/calc 表达式` | 计算器 |
| `/uuid` | 生成 UUID |
| `/ip` | 服务器 IP |

## 环境变量

### 基础配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WECHAT_ENTRY_HOST` | `szfilehelper.weixin.qq.com` | 入口域名 |
| `DOWNLOAD_DIR` | `./downloads` | 下载目录 |
| `AUTO_DOWNLOAD` | `1` | 自动下载文件 |
| `FILE_DATE_SUBDIR` | `1` | 按日期分子目录 |
| `FILE_RETENTION_DAYS` | `0` | 文件保留天数 (0=永久) |

### 插件与存储

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PLUGINS_DIR` | `./plugins` | 插件目录 |
| `MESSAGE_DB_PATH` | `./messages.db` | 消息数据库路径 |
| `ROBOT_TASK_FILE` | `./scheduled_tasks.json` | 任务持久化文件 |

### 聊天助手

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CHATBOT_ENABLED` | `0` | 启用聊天模式 |
| `CHATBOT_WEBHOOK_URL` | - | 聊天 Webhook |
| `CHATBOT_TIMEOUT` | `20` | 超时秒数 |

### Webhook 推送

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MESSAGE_WEBHOOK_URL` | - | 消息推送 Webhook |
| `MESSAGE_WEBHOOK_TIMEOUT` | `10` | 推送超时 |
| `LOGIN_CALLBACK_URL` | - | 登录成功回调 |

### 稳定性配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HEARTBEAT_INTERVAL` | `30` | 心跳间隔秒数 |
| `RECONNECT_DELAY` | `5` | 重连延迟秒数 |
| `MAX_RECONNECT_ATTEMPTS` | `10` | 最大重连次数 |

### 安全控制

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ROBOT_HTTP_ALLOWLIST` | - | HTTP 请求白名单 (逗号分隔) |

### Trace 抓包

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WECHAT_TRACE_ENABLED` | `1` | 启用协议抓包 |
| `WECHAT_TRACE_REDACT` | `1` | 脱敏敏感字段 |
| `WECHAT_TRACE_MAX_BODY` | `4096` | 最大 body 长度 |
| `WECHAT_TRACE_DIR` | `./trace_logs` | 日志目录 |

## 项目结构

```
.
├── main.py              # FastAPI 服务入口
├── direct_bot.py        # 微信协议客户端
├── processor.py         # 命令处理器
├── plugin_base.py       # 插件基类和装饰器
├── plugin_loader.py     # 插件加载器
├── message_store.py     # 消息持久化 (SQLite)
├── plugins/             # 插件目录
│   ├── builtin.py       # 内置命令
│   └── example.py       # 示例插件
├── downloads/           # 下载文件目录
│   └── 2024-01-15/      # 按日期分目录
├── messages.db          # 消息数据库
├── state.json           # 会话状态
├── scheduled_tasks.json # 定时任务
└── trace_logs/          # 协议日志
```

## Webhook 集成示例

### 消息推送

设置 `MESSAGE_WEBHOOK_URL` 后，每条消息会推送到你的服务：

```json
{
  "update_id": 123,
  "message": {
    "message_id": "1234567890",
    "date": 1705312345,
    "text": "消息内容",
    "type": "text",
    "document": null
  }
}
```

### 聊天回复

设置 `CHATBOT_WEBHOOK_URL` 后，聊天消息会发送到你的服务，期望返回：

```json
{
  "reply": "回复内容"
}
```

## 与 Telegram Bot API 对比

| Telegram | 本框架 | 说明 |
|----------|--------|------|
| `getUpdates` | `/bot/getUpdates` | 完全兼容 offset/limit |
| `sendMessage` | `/bot/sendMessage` | 支持 chat_id, reply_to_message_id, parse_mode |
| `sendDocument` | `/bot/sendDocument` | 支持 document, caption |
| `sendPhoto` | `/bot/sendPhoto` | 支持 photo, caption |
| `getMe` | `/bot/getMe` | 返回机器人信息 |
| `getChat` | `/bot/getChat` | 返回 filehelper 信息 |
| `getFile` | `/bot/getFile` | 获取文件下载路径 |
| `setWebhook` | `/bot/setWebhook` | 设置消息推送 |
| `deleteWebhook` | `/bot/deleteWebhook` | 删除 Webhook |
| `getWebhookInfo` | `/bot/getWebhookInfo` | 查看 Webhook 状态 |

## Python SDK

提供类似 `python-telegram-bot` 的 SDK，减少迁移工作：

```python
from filehelper_sdk import Bot, Updater

# 创建客户端
bot = Bot("http://127.0.0.1:8000")

# 发送消息
bot.send_message(text="Hello!")

# 发送文件
bot.send_document(file_path="/path/to/file.pdf", caption="文件说明")

# 获取更新 (自动管理 offset)
updates = bot.get_updates()
for update in updates:
    print(f"收到: {update.message.text}")

# 执行命令
result = bot.execute_command("/status")
print(result)
```

### 轮询模式

```python
from filehelper_sdk import Bot, Updater, Update

bot = Bot("http://127.0.0.1:8000")

def handle_message(update: Update):
    text = update.message.text
    print(f"收到消息: {text}")

    # 回复消息
    if text == "ping":
        bot.send_message(
            text="pong",
            reply_to_message_id=update.message.message_id
        )

updater = Updater(bot)
updater.add_handler(handle_message)
updater.start_polling()  # 阻塞运行
```

### 异步使用

```python
import asyncio
from filehelper_sdk import AsyncBot

async def main():
    bot = AsyncBot("http://127.0.0.1:8000")

    # 发送消息
    await bot.send_message(text="Hello!")

    # 获取更新
    updates = await bot.get_updates()
    for update in updates:
        print(update.message.text)

    await bot.close()

asyncio.run(main())
```

## 迁移指南 (从 Telegram Bot)

### 方式一：直接替换 API 地址

```python
# 原 Telegram 代码
import requests
BASE_URL = "https://api.telegram.org/bot<TOKEN>/"

# 改为
BASE_URL = "http://your-server:8000/bot/"

# 其他代码几乎不用改
requests.post(f"{BASE_URL}sendMessage", json={"text": "Hello", "chat_id": 123})
```

### 方式二：使用 SDK

```python
# 原 python-telegram-bot 代码
from telegram import Bot
bot = Bot(token="YOUR_TOKEN")
bot.send_message(chat_id=123, text="Hello")

# 改为
from filehelper_sdk import Bot
bot = Bot("http://your-server:8000")
bot.send_message(text="Hello")  # chat_id 会被忽略
```

### 参数兼容性

| 参数 | 支持 | 说明 |
|------|------|------|
| `chat_id` | 忽略 | 只有 filehelper 一个对话 |
| `text` | 完全支持 | - |
| `reply_to_message_id` | 完全支持 | - |
| `parse_mode` | 忽略 | 微信不支持 Markdown |
| `disable_notification` | 忽略 | - |
| `caption` | 完全支持 | 文件说明 |

## 对话指令菜单

发送 `/start` 或 `/m` 查看分类菜单：

```
📋 FileHelper Bot v2.0

【快捷入口】
/status - 查看状态
/help - 命令列表
/m - 快捷菜单

【功能分类】
/m server - 服务器管理
/m file - 文件操作
/m task - 定时任务
/m chat - 聊天助手
/m tools - 实用工具
```

## License

MIT
