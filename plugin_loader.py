"""
插件加载器 - 自动发现并加载 plugins/ 目录下的所有插件

支持两种插件格式:
1. 文件夹插件 (推荐): plugins/插件名/__init__.py
2. 单文件插件 (兼容): plugins/插件名.py

文件夹插件可以包含资源文件 (HTML, CSS, JS, 图片等)
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import plugin_base


class PluginLoader:
    def __init__(self, plugins_dir: str | Path | None = None):
        self.plugins_dir = Path(plugins_dir or os.path.join(os.getcwd(), "plugins"))
        self.loaded_plugins: dict[str, Any] = {}
        self.plugin_paths: dict[str, Path] = {}  # 插件名 -> 插件目录路径
        self.load_errors: list[dict[str, Any]] = []

    def load_all(self) -> dict[str, Any]:
        """加载 plugins/ 目录下所有插件 (优先文件夹，兼容单文件)"""
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return {}

        self.load_errors.clear()

        # 收集所有插件 (文件夹优先)
        plugins_to_load: list[tuple[str, Path, bool]] = []  # (name, path, is_package)

        # 1. 扫描文件夹插件
        for item in sorted(self.plugins_dir.iterdir()):
            if item.is_dir() and not item.name.startswith("_"):
                init_file = item / "__init__.py"
                if init_file.exists():
                    plugins_to_load.append((item.name, init_file, True))

        # 2. 扫描单文件插件 (兼容模式，跳过已有同名文件夹的)
        loaded_names = {p[0] for p in plugins_to_load}
        for file_path in sorted(self.plugins_dir.glob("*.py")):
            if file_path.name.startswith("_"):
                continue
            name = file_path.stem
            if name not in loaded_names:
                plugins_to_load.append((name, file_path, False))

        # 加载所有插件
        for name, path, is_package in plugins_to_load:
            try:
                module = self._load_module(name, path, is_package)
                self.loaded_plugins[name] = module
                self.plugin_paths[name] = path.parent if is_package else path
                plugin_type = "package" if is_package else "file"
                print(f"[PluginLoader] Loaded: {name} ({plugin_type})")
            except Exception as exc:
                error_info = {
                    "file": str(path.relative_to(self.plugins_dir)),
                    "error": str(exc),
                }
                self.load_errors.append(error_info)
                print(f"[PluginLoader] Failed to load {name}: {exc}")

        return self.loaded_plugins

    def _load_module(self, name: str, file_path: Path, is_package: bool) -> Any:
        """动态加载单个模块"""
        module_name = f"plugins.{name}"

        # 如果是包，需要设置 __path__
        spec = importlib.util.spec_from_file_location(
            module_name,
            file_path,
            submodule_search_locations=[str(file_path.parent)] if is_package else None,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec for {file_path}")

        module = importlib.util.module_from_spec(spec)

        # 设置插件目录路径，方便插件访问自己的资源
        module.__plugin_dir__ = file_path.parent if is_package else file_path.parent

        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def get_plugin_path(self, plugin_name: str) -> Path | None:
        """获取插件目录路径"""
        return self.plugin_paths.get(plugin_name)

    def get_plugin_resource(self, plugin_name: str, resource_path: str) -> Path | None:
        """获取插件资源文件路径"""
        plugin_dir = self.plugin_paths.get(plugin_name)
        if not plugin_dir:
            return None

        # 对于文件夹插件，资源在插件目录下
        if plugin_dir.is_dir():
            resource = plugin_dir / resource_path
        else:
            # 对于单文件插件，资源在同级目录
            resource = plugin_dir.parent / resource_path

        return resource if resource.exists() else None

    def reload_all(self) -> dict[str, Any]:
        """重新加载所有插件"""
        plugin_base.clear_registry()
        self.loaded_plugins.clear()
        self.plugin_paths.clear()
        return self.load_all()

    def get_status(self) -> dict[str, Any]:
        """获取插件加载状态"""
        return {
            "plugins_dir": str(self.plugins_dir),
            "loaded_count": len(self.loaded_plugins),
            "loaded_plugins": list(self.loaded_plugins.keys()),
            "errors": self.load_errors,
            "commands_count": len(plugin_base.get_registered_commands()),
            "handlers_count": len(plugin_base.get_message_handlers()),
            "routes_count": len(plugin_base.get_registered_routes()),
        }

    def register_routes(self, app) -> int:
        """将插件路由注册到 FastAPI app"""
        routes = plugin_base.get_registered_routes()
        registered = 0

        for route_info in routes:
            method = route_info.method.upper()
            path = route_info.path
            handler = route_info.handler
            tags = route_info.tags or ["Plugins"]

            if method == "GET":
                app.get(path, tags=tags)(handler)
            elif method == "POST":
                app.post(path, tags=tags)(handler)
            elif method == "PUT":
                app.put(path, tags=tags)(handler)
            elif method == "DELETE":
                app.delete(path, tags=tags)(handler)
            elif method == "PATCH":
                app.patch(path, tags=tags)(handler)
            else:
                print(f"[PluginLoader] Unknown HTTP method: {method}")
                continue

            registered += 1
            print(f"[PluginLoader] Registered route: {method} {path}")

        return registered
