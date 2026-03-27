import threading
import time
import requests
from flask import Flask

# =========================
# Flask app صغير للتشغيل
# =========================
app = Flask("bot_ping_app")

@app.route("/")
def index():
    return "Bot is alive ✅"

def run_flask():
    # شغّل الخادم على كل العناوين وبورت 10000
    app.run(host="0.0.0.0", port=10000)

# =========================
# Ping داخلي للبقاء نشط
# =========================
def keep_alive(url):
    while True:
        try:
            requests.get(url)
        except Exception:
            pass
        time.sleep(600)  # كل 10 دقائق

# =========================
# بدء كل شيء
# =========================
if __name__ == "__main__":
    # 1. شغّل خادم Flask في thread منفصل
    threading.Thread(target=run_flask, daemon=True).start()

    # 2. شغّل Ping داخلي على URL البوت
    # استبدل هذا بالـ URL العام للبوت على Render
    bot_url = "https://liben-8jz0.onrender.com"
    threading.Thread(target=keep_alive, args=(bot_url,), daemon=True).start()

    # 3. شغّل البوت العادي
    from main import start_bot  # دالة تبدأ polling للبوت
    start_bot()
