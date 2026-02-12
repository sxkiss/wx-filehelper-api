<!-- AUTO-DOC: Update me when project structure or architecture changes -->

# Architecture

本项目是一个 FastAPI 服务，提供 Telegram Bot API 风格的 HTTP 接口，并通过直连协议与微信「文件传输助手」交互。
核心由 `main.py` 负责生命周期编排；`direct_bot.py` 负责微信协议；`processor.py` 负责命令/插件/存储整合；`routes/` 提供 HTTP 路由；`plugins/` 扩展命令与管理界面。
容器化运行时通过 `docker-compose.yml` 将宿主机 `./data` 挂载到容器 `/data`，并以 `/data` 作为工作目录持久化运行时文件；对外端口为 `8070` 映射到容器内 `8000`。

## Index

- `INDEX.md`
- `routes/INDEX.md`
- `plugins/INDEX.md`
- `plugins/builtin/INDEX.md`
- `plugins/example/INDEX.md`
- `plugins/framework_api/INDEX.md`
- `plugins/webui/INDEX.md`
