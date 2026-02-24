import http.server
import socketserver
import webbrowser
from pathlib import Path
import os

PORT = 5500

# Папка frontend (рядом с этим файлом)
ROOT = Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        # Всегда обслуживаем файлы из папки ROOT
        path = super().translate_path(path)
        rel = Path(path).relative_to(Path.cwd())
        return str(ROOT / rel)


if __name__ == "__main__":
    # Меняем cwd, чтобы SimpleHTTPRequestHandler работал корректно
    os.chdir(str(ROOT))

    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/terminal/index.html"
        print(f"Frontend server running: {url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        httpd.serve_forever()
