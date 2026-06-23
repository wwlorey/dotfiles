#!/usr/bin/env python3
"""dic-daemon — keeps Kokoro-MLX loaded and serves synthesis over a Unix socket.

Protocol: line-delimited JSON over /tmp/dic.sock.
Request:  {"action": "speak"|"save"|"list_voices"|"ping"|"reset",
           "text": str, "voice": str, "speed": float, "lang": str,
           "output": str (for save)}
Response: {"ok": true} or {"ok": false, "error": str}, terminated by newline.

Model loads lazily on first speak/save/list_voices request so launchd
startup stays fast.
"""

from __future__ import annotations

import fcntl
import json
import os
import queue
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback

import numpy as np

SOCKET_PATH = "/tmp/dic.sock"
LOCK_PATH = "/tmp/dic-daemon.lock"
DEFAULT_VOICE = "bf_isabella"
SAMPLE_RATE = 24000
PLAYBACK_TIMEOUT = 300.0  # wall-clock cap on a single synth+play

# Cadence at which the writer pushes a silence frame when no real audio is
# queued. Each frame is small enough that ffplay's input pipe never holds
# more than a tick of latency, so a real utterance is heard within ~40ms of
# being enqueued, while the constant flow keeps CoreAudio out of low-power
# state and avoids the per-utterance device cold-start that used to clip
# the head of every speak.
PLAYER_IDLE_TICK_S = 0.04
SILENCE_FRAME = bytes(int(SAMPLE_RATE * PLAYER_IDLE_TICK_S) * 2)  # mono int16

_tts = None
_tts_lock = threading.Lock()
# kokoro_mlx.generate_stream is not lock-protected internally, so serialize
# every synthesis call across the whole daemon.
_synth_lock = threading.Lock()

# A single long-lived ffplay owns the audio device for the daemon's lifetime.
# All speakers funnel PCM through _audio_queue; the writer thread drains it
# into ffplay's stdin and pushes silence frames when idle so the device never
# closes. PortAudio still lives entirely inside the ffplay child, so a
# CoreAudio wedge is a bounded subprocess kill (writer detects BrokenPipe
# and respawns), not a daemon-wide deadlock.
_player: subprocess.Popen | None = None
_player_lock = threading.Lock()
_audio_queue: queue.Queue = queue.Queue()
_writer_thread: threading.Thread | None = None


def get_tts():
    global _tts
    with _tts_lock:
        if _tts is None:
            from kokoro_mlx import KokoroTTS
            _tts = KokoroTTS.from_pretrained()
        return _tts


def _spawn_player() -> subprocess.Popen:
    return subprocess.Popen(
        [
            "ffplay", "-nodisp", "-loglevel", "error",
            "-f", "s16le", "-ar", str(SAMPLE_RATE),
            "-ch_layout", "mono", "-i", "pipe:0",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def _ensure_player_alive() -> subprocess.Popen:
    """Spawn ffplay if it isn't running; return the current handle."""
    global _player
    with _player_lock:
        if _player is None or _player.poll() is not None:
            _player = _spawn_player()
        return _player


def _kill_player() -> None:
    """Tear down the current ffplay so the next write spawns a fresh one.

    Used by `reset` to re-initialize the audio device after a CoreAudio
    wedge (sleep/wake, device hot-swap).
    """
    global _player
    with _player_lock:
        if _player is not None and _player.poll() is None:
            _player.kill()
            try:
                _player.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        _player = None


def _writer_loop() -> None:
    """Drain _audio_queue into ffplay, streaming silence when idle.

    Continuous output keeps ffplay's stdin pipe active and CoreAudio's
    output unit out of low-power state, eliminating the per-utterance
    cold-start that clipped the head of every speak when agent turns
    left long silent gaps between dic calls.
    """
    global _player
    while True:
        try:
            item = _audio_queue.get(timeout=PLAYER_IDLE_TICK_S)
            chunks, done_event, err_holder = item
        except queue.Empty:
            chunks, done_event, err_holder = [SILENCE_FRAME], None, None

        err = ""
        for pcm in chunks:
            player = _ensure_player_alive()
            try:
                player.stdin.write(pcm)
                player.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                err = f"ffplay write failed: {e}"
                with _player_lock:
                    if _player is player:
                        _player = None
                break

        if done_event is not None:
            if err_holder is not None:
                err_holder["err"] = err
            done_event.set()


def _ensure_writer_started() -> None:
    global _writer_thread
    if _writer_thread is None or not _writer_thread.is_alive():
        _writer_thread = threading.Thread(target=_writer_loop, daemon=True)
        _writer_thread.start()


def _speak_via_ffplay(tts, text: str, **kwargs) -> str:
    """Synthesize *text* with kokoro and enqueue PCM to the shared writer.

    Returns "" on success or a short error string on failure. The actual
    write to ffplay happens on the writer thread; this function waits for
    the writer to drain the utterance before returning, so the per-call
    JSON ack still reflects playback completion.
    """
    chunks: list[bytes] = []
    deadline = time.monotonic() + PLAYBACK_TIMEOUT
    for chunk in tts.generate_stream(text, **kwargs):
        if time.monotonic() > deadline:
            return "playback timed out during synth"
        pcm = (np.clip(chunk, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
        chunks.append(pcm)

    done = threading.Event()
    err_holder = {"err": ""}
    _audio_queue.put((chunks, done, err_holder))

    remaining = max(0.5, deadline - time.monotonic())
    if not done.wait(timeout=remaining):
        return "playback timed out waiting for writer"
    return err_holder["err"]


def handle(req: dict) -> dict:
    action = req.get("action", "speak")
    if action == "ping":
        return {"ok": True}
    if action == "reset":
        # Drop the loaded TTS instance and tear down the player so the
        # next speak/save call rebuilds Kokoro and reopens the audio
        # device. Fast (seconds, model is on-disk) vs the cold-start 30s
        # of a full launchctl bounce. Held under all three locks so an
        # in-flight synth + write finishes before the reset takes effect.
        global _tts
        with _tts_lock, _synth_lock:
            _tts = None
            _kill_player()
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
            err = _speak_via_ffplay(tts, text, **kwargs)
            if err:
                return {"ok": False, "error": f"audio: {err}"}
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


def acquire_singleton_lock() -> None:
    """Exit silently if another dic-daemon is already running.

    Without this, a client-side spawn fallback or a launchd restart
    racing an orphaned process produces two daemons fighting over
    /tmp/dic.sock — the symptom is silent TTS (the surviving socket
    binds, but the wrong daemon serves). The lock fd stays open for
    the life of the process; the OS releases it on exit.
    """
    fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("dic-daemon: another instance already running, exiting", flush=True)
        sys.exit(0)
    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()}\n".encode())
    globals()["_singleton_lock_fd"] = fd


def main() -> None:
    acquire_singleton_lock()

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

    # Start the writer up front so ffplay and CoreAudio are warm before
    # the first speak request arrives.
    _ensure_writer_started()

    print(f"dic-daemon listening on {SOCKET_PATH}", flush=True)
    while True:
        try:
            conn, _ = srv.accept()
        except OSError:
            break
        threading.Thread(target=serve_client, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
