#!/usr/bin/env python3
"""dic-daemon — keeps Kokoro-MLX loaded and serves synthesis over a Unix socket.

Protocol: line-delimited JSON over /tmp/dic.sock.
Request:  {"action": "speak"|"save"|"list_voices"|"ping",
           "text": str, "voice": str, "speed": float, "lang": str,
           "output": str (for save)}
Response: {"ok": true} or {"ok": false, "error": str}, terminated by newline.

Model loads lazily on first speak/save/list_voices request so launchd
startup stays fast.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import sys
import threading
import traceback

SOCKET_PATH = "/tmp/dic.sock"
DEFAULT_VOICE = "bf_isabella"

_tts = None
_tts_lock = threading.Lock()
# kokoro_mlx.generate_stream is not lock-protected internally, and the
# audio device can only voice one stream at a time, so serialize every
# synthesis call across the whole daemon.
_synth_lock = threading.Lock()


def get_tts():
    global _tts
    with _tts_lock:
        if _tts is None:
            from kokoro_mlx import KokoroTTS
            _tts = KokoroTTS.from_pretrained()
        return _tts


def handle(req: dict) -> dict:
    action = req.get("action", "speak")
    if action == "ping":
        return {"ok": True}
    if action == "list_voices":
        return {"ok": True, "voices": get_tts().list_voices()}

    text = req.get("text") or ""
    if not text:
        return {"ok": False, "error": "empty text"}

    voice = req.get("voice") or DEFAULT_VOICE
    speed = float(req.get("speed") or 1.0)
    lang = req.get("lang") or None

    kwargs = {"voice": voice, "speed": speed}
    if lang:
        kwargs["language"] = lang

    tts = get_tts()
    with _synth_lock:
        if action == "save":
            path = req.get("output")
            if not path:
                return {"ok": False, "error": "save requires output path"}
            tts.save(text, path, **kwargs)
            return {"ok": True, "output": path}
        if action == "speak":
            tts.speak(text, stream=True, **kwargs)
            return {"ok": True}
    return {"ok": False, "error": f"unknown action: {action}"}


def serve_client(conn: socket.socket) -> None:
    try:
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
        if not buf:
            return
        line = buf.split(b"\n", 1)[0]
        try:
            req = json.loads(line.decode("utf-8"))
        except Exception as e:
            resp = {"ok": False, "error": f"bad json: {e}"}
        else:
            try:
                resp = handle(req)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                resp = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main() -> None:
    if os.path.exists(SOCKET_PATH):
        try:
            os.unlink(SOCKET_PATH)
        except OSError:
            pass

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o600)
    srv.listen(8)

    def shutdown(*_: object) -> None:
        try:
            srv.close()
        finally:
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass
            sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print(f"dic-daemon listening on {SOCKET_PATH}", flush=True)
    while True:
        try:
            conn, _ = srv.accept()
        except OSError:
            break
        threading.Thread(target=serve_client, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
