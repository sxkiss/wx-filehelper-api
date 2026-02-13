<!-- AUTO-DOC: Update me when files in this folder change -->

# Root

FastAPI 服务入口与核心模块；同时包含容器化（Docker/Compose）相关文件。

## Files

| File | Role | Function |
|------|------|----------|
| `main.py` | Entry | FastAPI 应用入口、生命周期编排、路由注册 |
| `config.py` | Config | 环境变量/路径/运行时配置集中管理 |
| `direct_bot.py` | Core | 微信文件传输助手直连协议实现 |
| `processor.py` | Core | 命令分发、插件系统、任务调度、Webhook 推送 |
| `message_store.py` | Storage | SQLite 消息与文件元数据存储 |
| `background.py` | Runtime | 后台任务（心跳、重连、清理等） |
| `plugin_base.py` | Ext | 插件装饰器/注册表/依赖注入与钩子 |
| `plugin_loader.py` | Ext | 插件发现与动态加载 |
| `filehelper_sdk.py` | SDK | Python SDK（便于外部调用 API） |
| `requirements.txt` | Build | Python 依赖清单 |
| `README.md` | Docs | 使用说明与 API 文档 |
| `Dockerfile` | Build | 镜像构建定义（运行 `python /app/main.py`） |
| `docker-compose.yml` | Deploy | 默认拉取镜像运行（host `8070` -> container `8000`） |
| `docker-compose.local-build.yml` | Deploy | 本地构建镜像并运行（host `8070` -> container `8000`） |
| `.dockerignore` | Build | 缩小构建上下文、避免带入运行时/大文件 |
| `.github/` | CI | GitHub Actions 工作流（Docker 多架构构建与推送） |
