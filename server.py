import http.server
import socketserver
import socket
import os
import sys
import json
import urllib.parse
import mimetypes
import subprocess
import shutil
import time

PORT = 5050
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
CLIPBOARD_FILE = os.path.join(BASE_DIR, "clipboard.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

if not os.path.exists(CLIPBOARD_FILE):
    with open(CLIPBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump({"text": "", "updated_at": int(time.time())}, f)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_clipboard_data():
    try:
        with open(CLIPBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"text": "", "updated_at": int(time.time())}

def set_clipboard_data(text):
    data = {"text": text, "updated_at": int(time.time())}
    with open(CLIPBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    # optional: push to linux clipboard if wl-copy / xclip available
    if shutil.which("wl-copy"):
        try:
            p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"))
        except Exception:
            pass
    elif shutil.which("xclip"):
        try:
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"))
        except Exception:
            pass
    return data

def get_files_list():
    items = []
    if not os.path.exists(UPLOADS_DIR):
        return items
    for name in sorted(os.listdir(UPLOADS_DIR), reverse=True):
        fpath = os.path.join(UPLOADS_DIR, name)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            items.append({
                "name": name,
                "size": stat.st_size,
                "modified": int(stat.st_mtime),
            })
    return items

class WebDropHandler(http.server.BaseHTTPRequestHandler):
    def send_json(self, status_code, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")
            return

        if path == "/api/status":
            self.send_json(200, {
                "ok": True,
                "clipboard": get_clipboard_data(),
                "files": get_files_list(),
                "server_time": int(time.time())
            })
            return

        if path.startswith("/download/"):
            filename = urllib.parse.unquote(path[len("/download/"):])
            # prevent traversal
            safe_name = os.path.basename(filename)
            fpath = os.path.join(UPLOADS_DIR, safe_name)
            if os.path.exists(fpath) and os.path.isfile(fpath):
                mime, _ = mimetypes.guess_type(fpath)
                if not mime:
                    mime = "application/octet-stream"
                size = os.path.getsize(fpath)
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(size))
                self.send_header("Content-Disposition", f'inline; filename="{safe_name}"')
                self.end_headers()
                with open(fpath, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
            else:
                self.send_error(404, "File not found")
            return

        # Static assets
        clean_path = path.lstrip("/")
        static_file = os.path.join(STATIC_DIR, clean_path)
        if os.path.exists(static_file) and os.path.isfile(static_file):
            mime, _ = mimetypes.guess_type(static_file)
            with open(static_file, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime or "text/plain")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/clipboard":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                text = data.get("text", "")
                saved = set_clipboard_data(text)
                self.send_json(200, {"ok": True, "clipboard": saved})
            except Exception as e:
                self.send_json(400, {"ok": False, "error": str(e)})
            return

        if path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                self.send_json(400, {"ok": False, "error": "Content-Type must be multipart/form-data"})
                return

            try:
                boundary = content_type.split("boundary=")[1].encode()
                if b";" in boundary:
                    boundary = boundary.split(b";")[0]
                if boundary.startswith(b'"') and boundary.endswith(b'"'):
                    boundary = boundary[1:-1]
            except Exception:
                self.send_json(400, {"ok": False, "error": "Invalid boundary"})
                return

            content_length = int(self.headers.get("Content-Length", 0))
            remain = content_length
            line = self.rfile.readline()
            remain -= len(line)

            if not line.strip().startswith(b"--" + boundary):
                self.send_json(400, {"ok": False, "error": "Malformed multipart"})
                return

            uploaded_files = []

            while remain > 0:
                # Read headers of part
                part_headers = {}
                while True:
                    hline = self.rfile.readline()
                    remain -= len(hline)
                    if not hline or hline in (b"\r\n", b"\n"):
                        break
                    decoded_h = hline.decode("utf-8", errors="ignore").strip()
                    if ":" in decoded_h:
                        hk, hv = decoded_h.split(":", 1)
                        part_headers[hk.strip().lower()] = hv.strip()

                disposition = part_headers.get("content-disposition", "")
                filename = None
                if 'filename="' in disposition:
                    filename = disposition.split('filename="')[1].split('"')[0]
                elif "filename=" in disposition:
                    filename = disposition.split("filename=")[1].split(";")[0].strip()

                if filename:
                    # Clean filename
                    clean_name = os.path.basename(filename)
                    if not clean_name:
                        clean_name = f"upload_{int(time.time())}"
                    
                    # Avoid overwriting
                    target_path = os.path.join(UPLOADS_DIR, clean_name)
                    base, ext = os.path.splitext(clean_name)
                    c = 1
                    while os.path.exists(target_path):
                        target_path = os.path.join(UPLOADS_DIR, f"{base}_{c}{ext}")
                        clean_name = f"{base}_{c}{ext}"
                        c += 1

                    # Stream payload until boundary
                    boundary_marker = b"--" + boundary
                    with open(target_path, "wb") as out_f:
                        buffer = b""
                        while remain > 0:
                            chunk = self.rfile.read(min(remain, 65536))
                            remain -= len(chunk)
                            buffer += chunk
                            idx = buffer.find(boundary_marker)
                            if idx != -1:
                                data_to_write = buffer[:idx]
                                if data_to_write.endswith(b"\r\n"):
                                    data_to_write = data_to_write[:-2]
                                elif data_to_write.endswith(b"\n"):
                                    data_to_write = data_to_write[:-1]
                                out_f.write(data_to_write)
                                # rewind remainder
                                leftover = buffer[idx:]
                                # read rest of boundary line
                                b_line_end = leftover.find(b"\n")
                                if b_line_end != -1:
                                    b_line = leftover[:b_line_end+1]
                                    buffer = leftover[b_line_end+1:]
                                    if b"--" in b_line and b_line.strip().endswith(b"--"):
                                        remain = 0 # end of parts
                                break
                            else:
                                keep_len = len(boundary_marker) + 4
                                if len(buffer) > keep_len:
                                    out_f.write(buffer[:-keep_len])
                                    buffer = buffer[-keep_len:]
                    uploaded_files.append(clean_name)
                else:
                    # drain part without saving
                    while remain > 0:
                        chunk = self.rfile.read(min(remain, 65536))
                        remain -= len(chunk)
                        if b"--" + boundary in chunk:
                            break

            self.send_json(200, {"ok": True, "files": uploaded_files})
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/files/"):
            filename = urllib.parse.unquote(path[len("/api/files/"):])
            safe_name = os.path.basename(filename)
            fpath = os.path.join(UPLOADS_DIR, safe_name)
            if os.path.exists(fpath) and os.path.isfile(fpath):
                try:
                    os.remove(fpath)
                    self.send_json(200, {"ok": True, "message": f"{safe_name} deleted"})
                except Exception as e:
                    self.send_json(500, {"ok": False, "error": str(e)})
            else:
                self.send_json(404, {"ok": False, "error": "File not found"})
            return

        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        # minimal console logging
        sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {format % args}\n")

def run():
    port = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])

    ip = get_local_ip()
    url = f"http://{ip}:{port}"

    print("=" * 60)
    print("  LOCAL WEBDROP (iPhone <-> Arch Linux)")
    print("=" * 60)
    print(f"  URL Akses: {url}")
    print(f"  Folder Upload: {UPLOADS_DIR}")
    print("-" * 60)
    print("  Scan QR Code ini langsung di Camera iPhone:")
    print("-" * 60)

    # Print terminal QR code
    if shutil.which("qrencode"):
        try:
            subprocess.run(["qrencode", "-t", "ANSIUTF8", url])
        except Exception:
            pass
    else:
        print("  (Tip: install 'qrencode' untuk tampilan QR di terminal)")

    print("-" * 60)
    print("  Tekan Ctrl+C untuk berhenti.")
    print("=" * 60)

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(("", port), WebDropHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer dihentikan.")

if __name__ == "__main__":
    run()
