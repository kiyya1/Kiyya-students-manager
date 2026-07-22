import threading
import webview
from app import app

def start_server():
    app.run(port=5000, debug=False)

if __name__ == '__main__':
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    webview.create_window("School Registration System", "http://127.0.0.1:5000")
    webview.start()