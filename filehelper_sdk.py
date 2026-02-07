"""
FileHelper Bot SDK - Telegram Bot API 兼容的 Python 客户端

使用方式与 python-telegram-bot 类似，便于迁移现有代码。

示例:
    from filehelper_sdk import Bot

    bot = Bot("http://127.0.0.1:8000")

    # 发送消息
    bot.send_message(text="Hello!")

    # 获取更新
    updates = bot.get_updates(offset=0, limit=10)
    for update in updates:
        print(update["message"]["text"])

    # 发送文件
    bot.send_document(file_path="/path/to/file.pdf")

异步使用:
    from filehelper_sdk import AsyncBot

    bot = AsyncBot("http://127.0.0.1:8000")
    await bot.send_message(text="Hello!")
"""

import time
from typing import Any
from dataclasses import dataclass

import httpx


@dataclass
class Message:
    """消息对象"""
    message_id: str
    date: int
    text: str
    type: str = "text"
    document: dict | None = None
    reply_to_message_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            message_id=data.get("message_id", ""),
            date=data.get("date", 0),
            text=data.get("text", ""),
            type=data.get("type", "text"),
            document=data.get("document"),
            reply_to_message_id=data.get("reply_to_message_id"),
        )


@dataclass
class Update:
    """更新对象"""
    update_id: int
    message: Message

    @classmethod
    def from_dict(cls, data: dict) -> "Update":
        return cls(
            update_id=data.get("update_id", 0),
            message=Message.from_dict(data.get("message", {})),
        )


class Bot:
    """
    同步版 FileHelper Bot 客户端

    兼容 Telegram Bot API 风格
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        self._offset = 0

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.base_url}{endpoint}"
        resp = self._client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, json: dict | None = None) -> dict:
        return self._request("POST", endpoint, json=json or {})

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        return self._request("GET", endpoint, params=params or {})

    # === Telegram Bot API 兼容方法 ===

    def get_me(self) -> dict:
        """获取机器人信息"""
        return self._get("/bot/getMe")

    def get_updates(
        self,
        offset: int | None = None,
        limit: int = 100,
        timeout: int = 0,
        auto_offset: bool = True,
    ) -> list[Update]:
        """
        获取消息更新

        Args:
            offset: 从此 update_id 之后开始获取
            limit: 最大返回数量
            timeout: 长轮询超时 (暂不支持)
            auto_offset: 自动更新 offset
        """
        if offset is None:
            offset = self._offset

        result = self._get("/bot/getUpdates", params={
            "offset": offset,
            "limit": limit,
            "timeout": timeout,
        })

        updates = [Update.from_dict(u) for u in result.get("result", [])]

        if auto_offset and updates:
            self._offset = updates[-1].update_id + 1

        return updates

    def send_message(
        self,
        text: str,
        chat_id: str | int | None = None,
        reply_to_message_id: str | int | None = None,
        parse_mode: str | None = None,
    ) -> dict:
        """
        发送文本消息

        Args:
            text: 消息内容
            chat_id: 忽略 (只有 filehelper)
            reply_to_message_id: 回复的消息ID
            parse_mode: 解析模式 (暂不支持)
        """
        return self._post("/bot/sendMessage", json={
            "text": text,
            "chat_id": chat_id,
            "reply_to_message_id": reply_to_message_id,
            "parse_mode": parse_mode,
        })

    def send_document(
        self,
        document: str | None = None,
        file_path: str | None = None,
        chat_id: str | int | None = None,
        reply_to_message_id: str | int | None = None,
        caption: str | None = None,
    ) -> dict:
        """
        发送文件

        Args:
            document: 文件路径 (TG 原生参数名)
            file_path: 文件路径 (本框架扩展)
            chat_id: 忽略
            reply_to_message_id: 回复的消息ID
            caption: 文件说明
        """
        return self._post("/bot/sendDocument", json={
            "document": document,
            "file_path": file_path,
            "chat_id": chat_id,
            "reply_to_message_id": reply_to_message_id,
            "caption": caption,
        })

    def send_photo(
        self,
        photo: str | None = None,
        file_path: str | None = None,
        chat_id: str | int | None = None,
        reply_to_message_id: str | int | None = None,
        caption: str | None = None,
    ) -> dict:
        """发送图片"""
        return self._post("/bot/sendPhoto", json={
            "photo": photo,
            "file_path": file_path,
            "chat_id": chat_id,
            "reply_to_message_id": reply_to_message_id,
            "caption": caption,
        })

    def get_chat(self, chat_id: str | int | None = None) -> dict:
        """获取聊天信息"""
        return self._get("/bot/getChat", params={"chat_id": chat_id})

    def get_file(self, file_id: str) -> dict:
        """获取文件信息"""
        return self._get("/bot/getFile", params={"file_id": file_id})

    def set_webhook(self, url: str, secret_token: str | None = None) -> dict:
        """设置 Webhook"""
        return self._post("/bot/setWebhook", json={
            "url": url,
            "secret_token": secret_token,
        })

    def delete_webhook(self) -> dict:
        """删除 Webhook"""
        return self._post("/bot/deleteWebhook")

    def get_webhook_info(self) -> dict:
        """获取 Webhook 信息"""
        return self._get("/bot/getWebhookInfo")

    # === 扩展方法 ===

    def execute_command(self, command: str, send_back: bool = False) -> dict:
        """执行机器人命令"""
        return self._post("/framework/execute", json={
            "command": command,
            "send_back": send_back,
        })

    def get_status(self) -> dict:
        """获取服务状态"""
        return self._get("/")

    def health_check(self) -> dict:
        """健康检查"""
        return self._get("/health")

    def get_store_stats(self) -> dict:
        """获取消息存储统计"""
        return self._get("/store/stats")

    def get_messages(self, limit: int = 50, offset: int = 0) -> dict:
        """获取历史消息"""
        return self._get("/store/messages", params={"limit": limit, "offset": offset})

    def list_downloads(self, limit: int = 100) -> dict:
        """列出下载的文件"""
        return self._get("/downloads", params={"limit": limit})

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            status = self._get("/login/status")
            return status.get("logged_in", False)
        except Exception:
            return False

    def close(self):
        """关闭客户端"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AsyncBot:
    """
    异步版 FileHelper Bot 客户端

    用于 asyncio 环境
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
        self._offset = 0

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.base_url}{endpoint}"
        resp = await self._client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, endpoint: str, json: dict | None = None) -> dict:
        return await self._request("POST", endpoint, json=json or {})

    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        return await self._request("GET", endpoint, params=params or {})

    async def get_me(self) -> dict:
        return await self._get("/bot/getMe")

    async def get_updates(
        self,
        offset: int | None = None,
        limit: int = 100,
        timeout: int = 0,
        auto_offset: bool = True,
    ) -> list[Update]:
        if offset is None:
            offset = self._offset

        result = await self._get("/bot/getUpdates", params={
            "offset": offset,
            "limit": limit,
            "timeout": timeout,
        })

        updates = [Update.from_dict(u) for u in result.get("result", [])]

        if auto_offset and updates:
            self._offset = updates[-1].update_id + 1

        return updates

    async def send_message(
        self,
        text: str,
        chat_id: str | int | None = None,
        reply_to_message_id: str | int | None = None,
        parse_mode: str | None = None,
    ) -> dict:
        return await self._post("/bot/sendMessage", json={
            "text": text,
            "chat_id": chat_id,
            "reply_to_message_id": reply_to_message_id,
            "parse_mode": parse_mode,
        })

    async def send_document(
        self,
        document: str | None = None,
        file_path: str | None = None,
        chat_id: str | int | None = None,
        reply_to_message_id: str | int | None = None,
        caption: str | None = None,
    ) -> dict:
        return await self._post("/bot/sendDocument", json={
            "document": document,
            "file_path": file_path,
            "chat_id": chat_id,
            "reply_to_message_id": reply_to_message_id,
            "caption": caption,
        })

    async def send_photo(
        self,
        photo: str | None = None,
        file_path: str | None = None,
        chat_id: str | int | None = None,
        reply_to_message_id: str | int | None = None,
        caption: str | None = None,
    ) -> dict:
        return await self._post("/bot/sendPhoto", json={
            "photo": photo,
            "file_path": file_path,
            "chat_id": chat_id,
            "reply_to_message_id": reply_to_message_id,
            "caption": caption,
        })

    async def execute_command(self, command: str, send_back: bool = False) -> dict:
        return await self._post("/framework/execute", json={
            "command": command,
            "send_back": send_back,
        })

    async def get_status(self) -> dict:
        return await self._get("/")

    async def health_check(self) -> dict:
        return await self._get("/health")

    async def is_logged_in(self) -> bool:
        try:
            status = await self._get("/login/status")
            return status.get("logged_in", False)
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


# === 简易轮询处理器 ===

class Updater:
    """
    简易更新轮询器

    类似 python-telegram-bot 的 Updater

    示例:
        def handle_message(update: Update):
            print(f"收到: {update.message.text}")

        updater = Updater(bot)
        updater.add_handler(handle_message)
        updater.start_polling()  # 阻塞运行
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.handlers: list[callable] = []
        self._running = False

    def add_handler(self, handler: callable):
        """添加消息处理函数"""
        self.handlers.append(handler)

    def start_polling(self, interval: float = 1.0):
        """开始轮询 (阻塞)"""
        self._running = True
        print("[Updater] Polling started...")

        while self._running:
            try:
                updates = self.bot.get_updates(auto_offset=True)
                for update in updates:
                    for handler in self.handlers:
                        try:
                            handler(update)
                        except Exception as e:
                            print(f"[Updater] Handler error: {e}")
            except Exception as e:
                print(f"[Updater] Polling error: {e}")

            time.sleep(interval)

    def stop(self):
        """停止轮询"""
        self._running = False


# === 便捷函数 ===

def create_bot(base_url: str = "http://127.0.0.1:8000") -> Bot:
    """创建同步 Bot 实例"""
    return Bot(base_url)


def create_async_bot(base_url: str = "http://127.0.0.1:8000") -> AsyncBot:
    """创建异步 Bot 实例"""
    return AsyncBot(base_url)
