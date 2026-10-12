"""
Module giám sát ứng dụng (App Monitor & Controller)
Chuyển tiếp đến agent.core.app_controller để đảm bảo tính nhất quán kiến trúc.
"""
from agent.core.app_controller import AppController, compute_file_sha256, show_blocked_dialog_async

__all__ = ["AppController", "compute_file_sha256", "show_blocked_dialog_async"]
