import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("ENABLE_FILE_LOGS", "false")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/ghoststock.db")
os.environ.setdefault("UPLOAD_FOLDER", "/tmp/uploads")
os.environ.setdefault("QR_FOLDER", "/tmp/qrcodes")

from app import create_app

app = create_app()


