from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Liben Bot is Alive 🚀"


def run_flask():
    app.run(
        host="0.0.0.0",
        port=10000
    )