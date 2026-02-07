import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
MONITOR_DEFAULT_TTL = int(os.getenv("MONITOR_DEFAULT_TTL", "300")) # 5 minutes default
