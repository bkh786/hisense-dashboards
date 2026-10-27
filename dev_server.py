#!/usr/bin/env python3
"""
Hisense AI Copilot - Local Development Server (dev_server.py)
Serves static dashboard files and routes `/api/chat` requests matching Vercel Serverless behavior.
Usage: python3 dev_server.py [port]
"""

import os
import sys
import json
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Import backend chat logic
try:
    from api.chat import process_chat_query, get_status_dict, get_gemini_api_key
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from api.chat import process_chat_query, get_status_dict, get_gemini_api_key

DEFAULT_PORT = 8000


class LocalDevHandler(SimpleHTTPRequestHandler):
    """Handles static file serving + serverless /api/chat routing."""

    def end_headers(self):
        # Enable CORS for local testing
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # Route /api/chat health check
        clean_path = self.path.split("?")[0]
        if clean_path == "/api/chat":
            api_key = get_gemini_api_key()
            status_data = get_status_dict(api_key)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
            return

        # Default static file handling
        return super().do_GET()

    def do_POST(self):
        clean_path = self.path.split("?")[0]
        if clean_path == "/api/chat":
            api_key = get_gemini_api_key()
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            status_code, result = process_chat_query(body, api_key)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def run(port=DEFAULT_PORT):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

    target_port = port
    while is_port_in_use(target_port):
        print(f"[dev_server] Port {target_port} is in use. Trying {target_port + 1}...")
        target_port += 1

    server_address = ("0.0.0.0", target_port)
    httpd = HTTPServer(server_address, LocalDevHandler)
    
    api_key = get_gemini_api_key()
    key_status = "CONFIGURED (Green Pill)" if api_key else "MISSING (Red Pill - Add to .env)"

    print("=" * 65)
    print("🚀 HISENSE DASHBOARD & AI COPILOT DEV SERVER RUNNING")
    print("=" * 65)
    print(f"👉 Local URL:              http://localhost:{target_port}/")
    print(f"👉 Sales Dashboard:        http://localhost:{target_port}/index.html")
    print(f"👉 Display Comparison:     http://localhost:{target_port}/display_comparison.html")
    print(f"👉 AI Copilot Endpoint:    http://localhost:{target_port}/api/chat")
    print(f"👉 Server Key Status:      {key_status}")
    print("=" * 65)
    print("Press Ctrl+C to stop.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dev server...")
        httpd.server_close()


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    run(p)
