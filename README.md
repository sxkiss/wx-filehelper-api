# WeChat FileHelper API 🚀

一个基于 Playwright + FastAPI 的微信文件传输助手自动化框架。通过 HTTP API 将您的微信"文件传输助手"变成可编程的消息接口。

## ✨ 功能特性

- **双向通信**：通过 API 发送消息，后台自动接收并处理微信消息
- **会话持久化**：登录状态自动保存，重启无需重新扫码
- **命令系统**：内置可扩展的命令处理器（支持 `ping`、`screenshot`、`echo` 等）
- **文件传输**：支持发送文件到自己的微信

## 📦 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

## 🚀 快速开始

### 1. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动，同时会弹出一个 Chromium 浏览器窗口。

### 2. 登录微信

- 在弹出的浏览器窗口中会显示登录二维码
- 使用手机微信扫描二维码
- 在手机上点击"确认登录"

### 3. 使用 API

登录成功后，您可以通过以下接口与微信交互：

#### 检查状态
```bash
curl http://localhost:8000/
```

#### 发送文本消息
```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello from API!"}'
```

#### 上传文件
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/your/file.pdf"
```

#### 获取最近消息
```bash
curl http://localhost:8000/messages?limit=10
```

#### 保存会话状态
```bash
curl -X POST http://localhost:8000/save_session
```

## 📡 API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/` | 检查服务状态和登录状态 |
| `GET` | `/qr` | 获取登录二维码（PNG 图片） |
| `POST` | `/send` | 发送文本消息 |
| `POST` | `/upload` | 上传并发送文件 |
| `GET` | `/messages` | 获取最近的消息列表 |
| `POST` | `/save_session` | 手动保存会话状态 |
| `GET` | `/debug_html` | 获取当前页面 HTML（调试用） |

## 🤖 内置命令

通过微信"文件传输助手"向自己发送以下命令，服务器会自动响应：

| 命令 | 描述 | 示例响应 |
|------|------|----------|
| `ping` | 测试连通性 | `pong` |
| `help` | 显示帮助菜单 | `Available commands: ping, help, echo, screenshot` |
| `echo [内容]` | 回显内容 | 返回 `[内容]` 部分 |
| `screenshot` | 获取服务器浏览器截图 | 发送截图图片 |

## 🔧 扩展命令

编辑 `processor.py` 来添加自定义命令：

```python
# 在 CommandProcessor 类中添加
async def cmd_mycommand(self, args, full_text):
    """处理 mycommand 指令"""
    return f"你发送了: {' '.join(args)}"

# 在 __init__ 中注册
self.commands["mycommand"] = self.cmd_mycommand
```

## 📁 项目结构

```
wechat-filehelper-api/
├── main.py          # FastAPI 服务端入口
├── bot.py           # Playwright 浏览器自动化核心
├── processor.py     # 命令处理逻辑
├── requirements.txt # Python 依赖
├── state.json       # 会话状态文件（自动生成，已添加到 .gitignore）
└── .gitignore       # Git 忽略规则
```

## ⚠️ 注意事项

1. **不要关闭浏览器窗口**：在服务运行期间，请勿手动关闭弹出的 Chromium 窗口
2. **首次登录**：首次使用需要扫码登录，之后会话会被保存
3. **网络环境**：确保服务器能访问 `filehelper.weixin.qq.com`
4. **安全性**：此 API 无认证保护，生产环境请添加鉴权机制

## 📝 许可证

MIT License

---

Made with ❤️ by API automation
