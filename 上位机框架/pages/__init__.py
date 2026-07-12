# pages/__init__.py
from .admin_page import AdminPage

# 定义允许 from pages import * 加载的类
__all__ = [
    "AdminPage",
    # "CameraPage",
]