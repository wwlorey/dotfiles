#!/usr/bin/env python3
"""dic-daemon — keeps Kokoro-MLX loaded and serves synthesis over a Unix socket.

Protocol: line-delimited JSON over /tmp/dic.sock.
Request:  {"action": "speak"|"save"|"list_voices"|"ping"|"reset",
           "text": str, "voice": str, "speed": float, "lang": str,
           "output": str (for save)}
Response: {"ok": true} or {"ok": false, "error": str}, terminated by newline.

Model loads lazily on first speak/save/list_voices request so launchd
startup stays fast.

Playback architecture (the failure this design defends against is "alive but
silent": a player process that keeps running while its CoreAudio output unit
has gone dead after sleep/wake or a default-device change, so writes still
succeed and nothing is ever heard). Two cooperating pieces, both keeping
PortAudio out of this process — a CoreAudio wedge must be a bounded
subprocess kill, never a daemon-wide deadlock:

  * Warm-keeper — one long-lived ffplay fed continuous silence. Its only job
    is to hold the audio route live so per-utterance playback starts into an
    already-powered device (no cold-start head clip during the long idle gaps
    agent turns leave between calls). It never carries speech, so if its unit
    silently wedges the worst case is a single clipped syllable, never silent
    speech.
  * Per-utterance player — each `speak` plays through its OWN fresh
    `ffplay -autoexit`. Spawning fresh per call means it binds to the CURRENT
    default output device, exits when playback actually drains (so completion
    is observable), and surfaces a device-open failure via exit code / stderr.
    A duration gate catches the instant-exit silent case. This is why speech
    cannot go permanently silent: the audible content never rides the
    long-lived player that wedges.

A sleep/wake watcher respawns the warm-keeper on wake — the primary trigger
for a wedged unit — with no external dependency.
"""

from __future__ import annotations

import fcntl
import json
import os
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

# Silence padded onto every utterance.
#   LEAD absorbs the first I/O cycles of the output device so the opening
#   syllable is never clipped, even though the warm-keeper already holds the
#   device live (belt and braces for a device that switched or just woke).
#   TAIL covers CoreAudio's residual ring buffer: ffplay -autoexit exits on
#   input EOF, which precedes the device finishing its drain; without a tail
#   pad the last word is lost.
LEAD_SILENCE_S = 0.2
TAIL_SILENCE_S = 0.4
LEAD_SILENCE = bytes(int(SAMPLE_RATE * LEAD_SILENCE_S) * 2)  # mono int16
TAIL_SILENCE = bytes(int(SAMPLE_RATE * TAIL_SILENCE_S) * 2)

# Warm-keeper cadence: a small silence frame per tick keeps the CoreAudio
# output unit out of low-power state. Each frame is tiny so the pipe never
# holds more than a tick of latency.
WARMKEEP_TICK_S = 0.04
WARMKEEP_FRAME = bytes(int(SAMPLE_RATE * WARMKEEP_TICK_S) * 2)

# Sleep/wake detection without a dependency: if a WATCH_TICK_S sleep() spans
# far more wall-clock than requested, the machine suspended in between. Sleep/
# wake is the primary cause of a silently-wedged unit, so on detecting it we
# respawn the warm-keeper to rebind a fresh unit on the now-awake device.
WATCH_TICK_S = 2.0
SLEEP_GAP_S = WATCH_TICK_S + 5.0

# Markers ffplay/CoreAudio print to stderr when the output unit fails. Their
# presence means the device errored even if the process exited 0.
_AUDIO_ERR_MARKERS = ("PortAudio", "AUHAL", "PaMacCore", "kAudio", "CoreAudio")

FFPLAY_INPUT = [
    "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ch_layout", "mono", "-i", "pipe:0",
]

_tts = None
_tts_lock = threading.Lock()
# kokoro_mlx.generate_stream is not lock-protected internally, so serialize
# every synthesis call across the whole daemon.
_synth_lock = threading.Lock()

# Warm-keeper handle. Guarded by _warm_lock so the writer thread, the sleep
# watcher, and `reset` don't race on respawn.
_warm: subprocess.Popen | None = None
_warm_lock = threading.Lock()


def get_tts():
    global _tts
    with _tts_lock:
        if _tts is None:
            from kokoro_mlx import KokoroTTS
            _tts = KokoroTTS.from_pretrained()
        return _tts


def _spawn_warmkeeper() -> subprocess.Popen:
    return subprocess.Popen(
        ["ffplay", "-nodisp", "-loglevel", "error", *FFPLAY_INPUT],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _restart_warmkeeper() -> None:
    """Tear down the current warm-keeper and spawn a fresh one.

    Used on wake and on `reset` to rebind the output unit to the live device.
    """
    global _warm
    with _warm_lock:
        if _warm is not None and _warm.poll() is None:
            _warm.kill()
            try:
                _warm.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        _warm = _spawn_warmkeeper()


def _warmkeeper_loop() -> None:
    """Push a silence frame each tick so the output device stays powered.

    Respawns the warm-keeper if it dies (BrokenPipe). A wedged-but-alive
    warm-keeper is harmless — it only plays silence — and is recovered by the
    sleep/wake watcher.
    """
    global _warm
    while True:
        with _warm_lock:
            if _warm is None or _warm.poll() is not None:
                _warm = _spawn_warmkeeper()
            w = _warm
        try:
            w.stdin.write(WARMKEEP_FRAME)
            w.stdin.flush()
        except (BrokenPipeError, OSError):
            with _warm_lock:
                if _warm is w:
                    _warm = None
        time.sleep(WARMKEEP_TICK_S)


def _sleep_watch_loop() -> None:
    """Respawn the warm-keeper after the machine wakes from sleep."""
    last = time.monotonic()
    while True:
        time.sleep(WATCH_TICK_S)
        now = time.monotonic()
        if now - last > SLEEP_GAP_S:
            _restart_warmkeeper()
        last = now


def _play_pcm(pcm: bytes) -> str:
    """Play one utterance through a fresh, self-terminating ffplay.

    Returns "" on success or a short error string. Speech rides its own
    per-call `ffplay -autoexit` (not the warm-keeper) so the player binds to
    the current default device, exits when playback drains, and reports
    device failures. The warm-keeper having held the device live means this
    fresh player does not cold-start clip.
    """
    payload = LEAD_SILENCE + pcm + TAIL_SILENCE
    expected_s = len(payload) / 2 / SAMPLE_RATE

    try:
        player = subprocess.Popen(
            ["ffplay", "-nodisp", "-loglevel", "error", "-autoexit", *FFPLAY_INPUT],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return "ffplay not found on PATH"

    start = time.monotonic()
    try:
        _, stderr = player.communicate(input=payload, timeout=PLAYBACK_TIMEOUT)
    except subprocess.TimeoutExpired:
        player.kill()
        player.wait()
        return "playback timed out"
    elapsed = time.monotonic() - start

    err_text = (stderr or b"").decode("utf-8", "replace").strip().replace("\n", " ")

    if player.returncode != 0:
        return (f"ffplay exited {player.returncode}: {err_text[:200]}"
                if err_text else f"ffplay exited {player.returncode}")

    if any(m in err_text for m in _AUDIO_ERR_MARKERS):
        return f"output device error: {err_text[:200]}"

    # Duration gate: ffplay plays in real time, so a clip that "completed" far
    # faster than its own length was rendered into a dead/silent unit, not
    # heard. Catches the alive-but-silent instant-drain case.
    if elapsed < expected_s * 0.5:
        return (f"returned in {elapsed:.2f}s for {expected_s:.2f}s of audio; "
                "output device likely silent")
    return ""


def handle(req: dict) -> dict:
    action = req.get("action", "speak")
    if action == "ping":
        return {"ok": True}
    if action == "reset":
        # Drop the loaded TTS instance and rebind the audio device by
        # respawning the warm-keeper. Fast (seconds; model is on-disk) vs the
        # ~30s cold-start of a full launchctl bounce. The TTS drop is held
        # under both synth-related locks so an in-flight synth finishes first;
        # the warm-keeper respawn takes its own lock.
        global _tts
        with _tts_lock, _synth_lock:
            _tts = None
        _restart_warmkeeper()
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
            chunks: list[bytes] = []
            deadline = time.monotonic() + PLAYBACK_TIMEOUT
            for chunk in tts.generate_stream(text, **kwargs):
                if time.monotonic() > deadline:
                    return {"ok": False, "error": "audio: synth timed out"}
                pcm = (np.clip(chunk, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
                chunks.append(pcm)
            err = _play_pcm(b"".join(chunks))
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

    # Bring the audio device up front: the warm-keeper holds it warm and the
    # sleep watcher rebinds it on wake, so the first real speak starts into a
    # live device.
    threading.Thread(target=_warmkeeper_loop, daemon=True).start()
    threading.Thread(target=_sleep_watch_loop, daemon=True).start()

    print(f"dic-daemon listening on {SOCKET_PATH}", flush=True)
    while True:
        try:
            conn, _ = srv.accept()
        except OSError:
            break
        threading.Thread(target=serve_client, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
