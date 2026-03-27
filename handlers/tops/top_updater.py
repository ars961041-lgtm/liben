import threading
import time
from database.connection import get_all_group_ids
from handlers.tops.tops import get_top_activity, get_top_countries, get_top_messages  # دالة تجلب كل جروباتك

def update_all_tops():
    while True:
        try:
            print("🔄 Updating tops...")
            group_ids = get_all_group_ids()
            for group_id in group_ids:
                get_top_messages(group_id)
                get_top_activity(group_id)
            get_top_countries()
        except Exception as e:
            print("Error updating tops:", e)
        time.sleep(600)  # كل 10 دقائق

def start_top_updater():
    threading.Thread(target=update_all_tops, daemon=True).start()