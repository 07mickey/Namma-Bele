"""
Offline, pure-standard-library CDP screenshot utility for NAMMA BELE portal.
"""
import os
import sys
import time
import json
import socket
import base64
import struct
import subprocess
import urllib.request

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT_DIR = "/Users/manojv/.gemini/antigravity/brain/b5d0d17c-8450-4d74-aded-bf3c68079b42/screens/refined"
PORT = 9222

class SimpleWebSocket:
    def __init__(self, host, port, path):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        res = self.sock.recv(4096).decode(errors="ignore")
        if "101" not in res:
            raise RuntimeError(f"WebSocket handshake failed: {res}")

    def send_text(self, text):
        payload = text.encode("utf-8")
        length = len(payload)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        if length <= 125:
            header = struct.pack("!BB", 0x81, 0x80 | length) + mask
        elif length <= 65535:
            header = struct.pack("!BBH", 0x81, 0x80 | 126, length) + mask
        else:
            header = struct.pack("!BBQ", 0x81, 0x80 | 127, length) + mask
        self.sock.sendall(header + masked)

    def recv_text(self):
        buf = bytearray()
        while True:
            head = self.sock.recv(2)
            if not head:
                return ""
            b1, b2 = head
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack("!H", self.sock.recv(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self.sock.recv(8))[0]
            data = bytearray()
            while len(data) < length:
                chunk = self.sock.recv(length - len(data))
                if not chunk:
                    break
                data.extend(chunk)
            buf.extend(data)
            if b1 & 0x80:  # FIN bit set
                break
        return buf.decode("utf-8", errors="ignore")

    def close(self):
        try:
            self.sock.close()
        except:
            pass

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    user_data = "/tmp/chrome_cdp_" + str(int(time.time()))
    proc = subprocess.Popen([
        CHROME_BIN,
        "--headless=new",
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={user_data}",
        "--window-size=1280,950",
        "--disable-gpu",
        "--no-sandbox",
        "about:blank"
    ])
    try:
        time.sleep(2)
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json") as r:
            targets = json.loads(r.read().decode())
        ws_url = targets[0]["webSocketDebuggerUrl"]
        # Parse ws://127.0.0.1:9222/devtools/page/...
        path = ws_url.split(f":{PORT}")[1]

        ws = SimpleWebSocket("127.0.0.1", PORT, path)
        cmd_id = 0

        def send_cmd(method, params=None):
            nonlocal cmd_id
            cmd_id += 1
            this_id = cmd_id
            msg = {"id": this_id, "method": method, "params": params or {}}
            ws.send_text(json.dumps(msg))
            while True:
                raw = ws.recv_text()
                if not raw:
                    return {}
                try:
                    res = json.loads(raw)
                    if res.get("id") == this_id:
                        return res.get("result", {})
                except:
                    pass

        def capture(url, filename, wait=1.5):
            print(f"Navigating: {url} -> {filename}...")
            send_cmd("Page.navigate", {"url": url})
            time.sleep(wait)
            res = send_cmd("Page.captureScreenshot", {"format": "png"})
            if "data" in res:
                data = base64.b64decode(res["data"])
                out_path = os.path.join(OUT_DIR, filename)
                with open(out_path, "wb") as f:
                    f.write(data)
                print(f"  [✔] Wrote {out_path} ({len(data)} bytes)")
            else:
                print(f"  [!] Failed to capture {filename}: {res}")

        # 1. Homepage
        capture("http://127.0.0.1:5001/", "01_homepage_desktop.png", wait=2)

        # 2. Login Page
        capture("http://127.0.0.1:5001/login", "02_login_page_desktop.png", wait=1.5)

        # 3. Soil Guide
        capture("http://127.0.0.1:5001/soil-guide", "05_soil_guide.png", wait=2)

        # 4. Authenticate as Farmer Mallikarjuna (+919999000001)
        send_cmd("Page.navigate", {"url": "http://127.0.0.1:5001/login"})
        time.sleep(1.5)
        send_cmd("Runtime.evaluate", {
            "expression": """
                document.getElementById('login-phone').value = '+919999000001';
                document.getElementById('login-password').value = 'DemoUser@2026!';
                document.getElementById('btn-submit-login').click();
            """
        })
        time.sleep(2)

        # 5. Farmer Portal Dashboard
        capture("http://127.0.0.1:5001/farmer", "04_farmer_dashboard.png", wait=2)

        # 6. Farmer Sample Tracking
        capture("http://127.0.0.1:5001/farmer/tracking", "06_farmer_tracking.png", wait=2)

        # 7. Authenticate as Admin (+919999000008)
        send_cmd("Page.navigate", {"url": "http://127.0.0.1:5001/login"})
        time.sleep(1.5)
        send_cmd("Runtime.evaluate", {
            "expression": """
                document.getElementById('tab-staff-login').click();
                document.getElementById('login-phone').value = '+919999000008';
                document.getElementById('login-password').value = 'DemoUser@2026!';
                document.getElementById('btn-submit-login').click();
            """
        })
        time.sleep(2)

        # 8. Admin Dashboard
        capture("http://127.0.0.1:5001/admin", "07_admin_dashboard.png", wait=2)

        # 9. Admin Dispatch Queue
        capture("http://127.0.0.1:5001/admin/dispatch", "08_admin_dispatch.png", wait=2)

        ws.close()
        print("\nAll screenshots captured successfully!")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
