import webview
import threading
from app import app

def start_flask():
    # Run Flask app in a thread
    app.run(host="127.0.0.1", port=5000)

if __name__ == '__main__':
    # Start Flask in a separate thread
    threading.Thread(target=start_flask, daemon=True).start()
    
    # Launch the desktop app
    webview.create_window("My Flask App", "http://127.0.0.1:5000")
    webview.start()
