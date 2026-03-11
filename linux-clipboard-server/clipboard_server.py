#!/usr/bin/env python3
import io
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from flask import Flask, Response, jsonify, render_template_string
from PIL import Image, UnidentifiedImageError

app = Flask(__name__)

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Clipboard Image Relay</title>
  <style>
    :root {
      --bg: #f3efe5;
      --panel: rgba(255, 252, 246, 0.9);
      --ink: #152126;
      --muted: #56656d;
      --accent: #0a7b83;
      --accent-strong: #085f65;
      --border: rgba(21, 33, 38, 0.12);
      --shadow: 0 18px 45px rgba(21, 33, 38, 0.12);
      --radius: 24px;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", "Noto Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(10, 123, 131, 0.18), transparent 30%),
        radial-gradient(circle at bottom right, rgba(186, 120, 54, 0.16), transparent 28%),
        linear-gradient(160deg, #f7f2e7 0%, #efe7da 45%, #e3efe8 100%);
      display: grid;
      place-items: center;
      padding: 24px;
    }

    .shell {
      width: min(100%, 720px);
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
      backdrop-filter: blur(12px);
    }

    .hero {
      padding: 28px 24px 16px;
      border-bottom: 1px solid var(--border);
      background: linear-gradient(135deg, rgba(10, 123, 131, 0.08), rgba(255, 255, 255, 0));
    }

    h1 {
      margin: 0 0 8px;
      font-size: clamp(1.7rem, 4vw, 2.6rem);
      line-height: 1.05;
    }

    p {
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
    }

    .content {
      padding: 20px 24px 24px;
      display: grid;
      gap: 16px;
    }

    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    button {
      appearance: none;
      border: none;
      border-radius: 999px;
      padding: 14px 18px;
      font-size: 1rem;
      font-weight: 700;
      cursor: pointer;
      transition: transform 140ms ease, opacity 140ms ease, background 140ms ease;
    }

    button:hover { transform: translateY(-1px); }
    button:active { transform: translateY(0); }
    button:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }

    .primary {
      background: var(--accent);
      color: white;
    }

    .primary:hover { background: var(--accent-strong); }

    .secondary {
      background: white;
      color: var(--ink);
      border: 1px solid var(--border);
    }

    .status {
      min-height: 48px;
      border-radius: 16px;
      padding: 14px 16px;
      background: rgba(255, 255, 255, 0.8);
      border: 1px solid var(--border);
      color: var(--muted);
    }

    .frame {
      background: rgba(255, 255, 255, 0.85);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 14px;
      min-height: 280px;
      display: grid;
      place-items: center;
      overflow: hidden;
    }

    .placeholder {
      text-align: center;
      color: var(--muted);
      max-width: 320px;
    }

    img {
      max-width: 100%;
      max-height: 65vh;
      display: none;
      border-radius: 16px;
      box-shadow: 0 12px 28px rgba(21, 33, 38, 0.16);
    }

    .meta {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      font-size: 0.92rem;
      flex-wrap: wrap;
    }

    .warning {
      border-top: 1px solid var(--border);
      padding: 16px 24px 24px;
      color: var(--muted);
      font-size: 0.93rem;
    }

    code {
      background: rgba(21, 33, 38, 0.08);
      padding: 2px 6px;
      border-radius: 6px;
    }

    @media (max-width: 560px) {
      .actions {
        grid-template-columns: 1fr;
      }

      .hero, .content, .warning {
        padding-left: 18px;
        padding-right: 18px;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <h1>Clipboard Image Relay</h1>
      <p>Fetch the latest clipboard image from your Linux laptop over local Wi-Fi.</p>
    </section>

    <section class="content">
      <div class="actions">
        <button id="fetchBtn" class="primary">Fetch Image</button>
        <button id="downloadBtn" class="secondary" disabled>Download PNG</button>
      </div>

      <div id="status" class="status">Ready. Tap <strong>Fetch Image</strong> to pull the latest clipboard image.</div>

      <div class="frame">
        <div id="placeholder" class="placeholder">
          The image preview will appear here. New requests bypass cache automatically.
        </div>
        <img id="preview" alt="Clipboard preview">
      </div>

      <div class="meta">
        <span id="serverHint">Server: <code id="origin"></code></span>
        <span id="updatedAt">Last update: never</span>
      </div>
    </section>

    <section class="warning">
      Local network only. Do not expose this service to the public internet without adding authentication and TLS.
    </section>
  </main>

  <script>
    const fetchBtn = document.getElementById('fetchBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const preview = document.getElementById('preview');
    const placeholder = document.getElementById('placeholder');
    const statusEl = document.getElementById('status');
    const updatedAt = document.getElementById('updatedAt');
    const originEl = document.getElementById('origin');
    originEl.textContent = window.location.origin;

    let activeUrl = null;
    let latestBlob = null;

    function setStatus(message, isError = false) {
      statusEl.textContent = message;
      statusEl.style.color = isError ? '#9f2f2f' : 'var(--muted)';
      statusEl.style.background = isError ? 'rgba(255, 232, 232, 0.92)' : 'rgba(255, 255, 255, 0.8)';
    }

    async function fetchImage() {
      fetchBtn.disabled = true;
      downloadBtn.disabled = true;
      setStatus('Fetching clipboard image...');

      try {
        const response = await fetch(`/api/image?t=${Date.now()}`, {
          cache: 'no-store',
          headers: { 'Cache-Control': 'no-cache' }
        });

        if (!response.ok) {
          let message = `Server returned ${response.status}`;
          try {
            const payload = await response.json();
            if (payload.error) {
              message = payload.error;
            }
          } catch (_) {}
          throw new Error(message);
        }

        const blob = await response.blob();
        latestBlob = blob;

        if (activeUrl) {
          URL.revokeObjectURL(activeUrl);
        }

        activeUrl = URL.createObjectURL(blob);
        preview.src = activeUrl;
        preview.style.display = 'block';
        placeholder.style.display = 'none';
        downloadBtn.disabled = false;
        updatedAt.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
        setStatus('Image fetched successfully.');
      } catch (error) {
        latestBlob = null;
        preview.removeAttribute('src');
        preview.style.display = 'none';
        placeholder.style.display = 'block';
        setStatus(error.message || 'Failed to fetch clipboard image.', true);
      } finally {
        fetchBtn.disabled = false;
      }
    }

    function downloadImage() {
      if (!latestBlob) return;
      const anchor = document.createElement('a');
      anchor.href = activeUrl;
      anchor.download = `clipboard-${Date.now()}.png`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    }

    fetchBtn.addEventListener('click', fetchImage);
    downloadBtn.addEventListener('click', downloadImage);
  </script>
</body>
</html>
"""


@dataclass
class ClipboardPayload:
    png_bytes: bytes
    source: str
    mime_type: str


class ClipboardError(RuntimeError):
    pass


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, check=False)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def detect_session_backend() -> Optional[str]:
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type in {"wayland", "x11"}:
        return session_type

    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"

    if os.environ.get("DISPLAY"):
        return "x11"

    return None


def choose_wayland_mime() -> Optional[str]:
    list_result = run_command(["wl-paste", "--list-types"])
    if list_result.returncode != 0:
        stderr = list_result.stderr.decode("utf-8", errors="ignore").strip()
        raise ClipboardError(stderr or "wl-paste could not inspect clipboard types.")

    targets = {
        line.strip()
        for line in list_result.stdout.decode("utf-8", errors="ignore").splitlines()
        if line.strip()
    }

    for mime in ("image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"):
        if mime in targets:
            return mime
    return None


def choose_x11_mime() -> Optional[str]:
    list_result = run_command(["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"])
    if list_result.returncode != 0:
        stderr = list_result.stderr.decode("utf-8", errors="ignore").strip()
        raise ClipboardError(stderr or "xclip could not inspect clipboard targets.")

    targets = {
        line.strip()
        for line in list_result.stdout.decode("utf-8", errors="ignore").splitlines()
        if line.strip()
    }

    for mime in ("image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"):
        if mime in targets:
            return mime
    return None


def convert_to_png(image_bytes: bytes, mime_type: str) -> bytes:
    if mime_type == "image/png":
        return image_bytes

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            converted = io.BytesIO()
            image.save(converted, format="PNG")
            return converted.getvalue()
    except UnidentifiedImageError as exc:
        raise ClipboardError("Clipboard image format is unsupported.") from exc
    except OSError as exc:
        raise ClipboardError("Failed to convert clipboard image to PNG.") from exc


def read_wayland_clipboard() -> ClipboardPayload:
    if not command_exists("wl-paste"):
        raise ClipboardError("Wayland clipboard support requires wl-clipboard (`wl-paste`).")

    mime_type = choose_wayland_mime()
    if not mime_type:
        raise ClipboardError("Clipboard does not currently contain an image.")

    result = run_command(["wl-paste", "--no-newline", "--type", mime_type])
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="ignore").strip()
        raise ClipboardError(stderr or "Failed to read clipboard image from Wayland.")

    if not result.stdout:
        raise ClipboardError("Clipboard image is empty.")

    return ClipboardPayload(
        png_bytes=convert_to_png(result.stdout, mime_type),
        source="wayland",
        mime_type=mime_type,
    )


def read_x11_clipboard() -> ClipboardPayload:
    if not command_exists("xclip"):
        raise ClipboardError("X11 clipboard support requires xclip.")

    mime_type = choose_x11_mime()
    if not mime_type:
        raise ClipboardError("Clipboard does not currently contain an image.")

    result = run_command(["xclip", "-selection", "clipboard", "-t", mime_type, "-o"])
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="ignore").strip()
        raise ClipboardError(stderr or "Failed to read clipboard image from X11.")

    if not result.stdout:
        raise ClipboardError("Clipboard image is empty.")

    return ClipboardPayload(
        png_bytes=convert_to_png(result.stdout, mime_type),
        source="x11",
        mime_type=mime_type,
    )


def load_clipboard_image() -> ClipboardPayload:
    backend = detect_session_backend()
    errors = []

    backends = []
    if backend == "wayland":
        backends = [read_wayland_clipboard, read_x11_clipboard]
    elif backend == "x11":
        backends = [read_x11_clipboard, read_wayland_clipboard]
    else:
        backends = [read_wayland_clipboard, read_x11_clipboard]

    for reader in backends:
        try:
            return reader()
        except ClipboardError as exc:
            errors.append(str(exc))

    unique_errors = " | ".join(dict.fromkeys(errors))
    raise ClipboardError(unique_errors or "No clipboard backend is available.")


@app.after_request
def apply_no_cache_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def index() -> str:
    return render_template_string(INDEX_HTML)


@app.route("/api/image")
def get_clipboard_image() -> Response:
    try:
        payload = load_clipboard_image()
    except ClipboardError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:  # pragma: no cover
        app.logger.exception("Unexpected clipboard failure")
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500

    return Response(
        payload.png_bytes,
        mimetype="image/png",
        headers={
            "Content-Disposition": 'inline; filename="clipboard.png"',
            "X-Clipboard-Backend": payload.source,
            "X-Clipboard-Source-Mime": payload.mime_type,
        },
    )


@app.route("/api/status")
def status() -> Response:
    try:
        payload = load_clipboard_image()
        return jsonify(
            {
                "ok": True,
                "backend": payload.source,
                "source_mime": payload.mime_type,
                "size_bytes": len(payload.png_bytes),
            }
        )
    except ClipboardError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception as exc:  # pragma: no cover
        app.logger.exception("Unexpected status failure")
        return jsonify({"ok": False, "error": f"Unexpected server error: {exc}"}), 500


def main() -> int:
    host = os.environ.get("CLIPBOARD_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("CLIPBOARD_SERVER_PORT", "5000"))
    debug = os.environ.get("CLIPBOARD_SERVER_DEBUG", "").lower() in {"1", "true", "yes"}

    app.run(host=host, port=port, debug=debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
