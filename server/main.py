"""
Launcher cho FastAPI Server.
Lưu ý: Logic chính đã được cấu trúc tại server/app/main.py
"""
import sys
import os

os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

SYS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
if SYS_ROOT not in sys.path:
    sys.path.insert(0, SYS_ROOT)

from server.app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app.main:app", host="127.0.0.1", port=8000, reload=True)
