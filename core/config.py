import os
from dotenv import load_dotenv
load_dotenv()
# =========================
# MODE
# =========================
IS_TEST = os.environ.get("IS_TEST", "false").lower() == "true"

# =========================
# TOKENS
# =========================
if IS_TEST:
    TOKEN = os.environ.get("TEST_TOKEN")
else:
    TOKEN = os.environ.get("BOT_TOKEN")

# =========================
# DATABASE
# =========================
if IS_TEST:
    DB_NAME = "test_database.db"
else:
    DB_NAME = "database.db"

# =========================
# OTHER
# =========================
developers_id = {7632471789}
bot_name = "ليبن"

print("🧪 TEST MODE" if IS_TEST else "🚀 PRODUCTION MODE")
