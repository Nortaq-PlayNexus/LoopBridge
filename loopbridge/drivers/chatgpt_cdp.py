"""ChatGPT driver: Chrome DevTools Protocol (CDP) control of Brave.

Brave (Chromium) exposes CDP when launched with:

    brave.exe --remote-debugging-port=9222

This driver connects to that endpoint, runs JavaScript inside the ChatGPT
page, and reads/writes the DOM directly. It is far more robust than UIA tree
poking because the page's own React state does the work — we just evaluate
JS. Text is read straight out of the DOM (no clipboard round-trip needed).
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Optional

from ..config.profiles import ChatGPTConfig
from ..core.errors import CopyError, SendError
from ..core.text_engine import TextEngine
from .base import ChatGPTDriver

# --------------------------------------------------------------------- JS
JS_STATE = r"""
(() => {
  const msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
  if (!msgs.length) return { found: false };
  const last = msgs[msgs.length - 1];
  const copyBtn = last.querySelector('[data-testid="copy-button"], button[aria-label*="opy" i]');
  const stopBtn = document.querySelector('.stop-button, [data-testid="stop-button"], button[aria-label*="stop" i]');
  return {
    found: true,
    hasCopy: !!copyBtn,
    stopActive: !!stopBtn,
    length: (last.innerText || '').length
  };
})()
"""

JS_GET_REPLY = r"""
(() => {
  const msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
  if (!msgs.length) return '';
  const last = msgs[msgs.length - 1];
  return last.innerText || '';
})()
"""

JS_COMPOSER_FOCUS = r"""
(() => {
  const ta = document.querySelector('#prompt-textarea') || document.querySelector('textarea');
  if (!ta) return false;
  ta.focus();
  return true;
})()
"""

JS_SET_VALUE = r"""
(() => {
  const ta = document.querySelector('#prompt-textarea') || document.querySelector('textarea');
  if (!ta) return 'NO_TEXTAREA';
  const proto = ta.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
  setter.call(ta, __TEXT__);
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  return 'OK';
})()
"""

JS_SEND = r"""
(() => {
  const sendBtn = document.querySelector('button[data-testid="send-button"]');
  if (sendBtn && !sendBtn.disabled) { sendBtn.click(); return 'clicked'; }
  const ta = document.querySelector('#prompt-textarea') || document.querySelector('textarea');
  if (!ta) return 'NO_TEXTAREA';
  ta.focus();
  for (const type of ['keydown', 'keypress', 'keyup']) {
    ta.dispatchEvent(new KeyboardEvent(type, { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
  }
  return 'enter';
})()
"""

JS_CLEAR_COMPOSER = r"""
(() => {
  const ta = document.querySelector('#prompt-textarea') || document.querySelector('textarea');
  if (!ta) return 'NO_TEXTAREA';
  const proto = window.HTMLTextAreaElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
  setter.call(ta, '');
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  return 'OK';
})()
"""


class CdpChatGPTDriver(ChatGPTDriver):
    def __init__(self, port: int = 9222, url_contains: str = "chatgpt.com",
                 cfg: ChatGPTConfig = None, text: TextEngine = None, log=None) -> None:
        self.port = port
        self.url_contains = url_contains
        self.cfg = cfg or ChatGPTConfig()
        self.text = text or TextEngine()
        self._log = log or (lambda msg, level="info": None)
        self._ws = None
        self._target_id: Optional[str] = None
        self._msg_id = 0

    # ------------------------------------------------------------ connection
    def connect(self) -> None:
        import websocket  # type: ignore

        self._ensure_target()
        ws_url = self._websocket_url()
        self._ws = websocket.create_connection(ws_url, timeout=15)

    def _ensure_target(self) -> None:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=10) as resp:
            targets = json.load(resp)
        for t in targets:
            if self.url_contains.lower() in (t.get("url", "") or "").lower():
                self._target_id = t["id"]
                return
        # no tab yet — use the first page and navigate it
        for t in targets:
            if t.get("type") == "page":
                self._target_id = t["id"]
                self._evaluate("window.location.href = 'https://chatgpt.com/'")
                time.sleep(2.0)
                return
        raise SendError(f"No browser tabs found on CDP port {self.port}.")

    def _websocket_url(self) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=10) as resp:
            targets = json.load(resp)
        for t in targets:
            if t.get("id") == self._target_id and t.get("webSocketDebuggerUrl"):
                return t["webSocketDebuggerUrl"]
        raise SendError("CDP target disappeared; relaunch Brave with --remote-debugging-port.")

    def _evaluate(self, expression: str, timeout: float = 20.0):
        if self._ws is None:
            self.connect()
        self._msg_id += 1
        msg_id = self._msg_id
        self._ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True, "awaitPromise": True},
        }))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = self._ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("id") == msg_id:
                if "error" in data:
                    raise SendError(f"CDP evaluate error: {data['error']}")
                return data.get("result", {}).get("result", {}).get("value")
        raise SendError("CDP evaluate timed out.")

    # ------------------------------------------------------------ loop API
    def wait_for_reply_done(self, deadline: float) -> None:
        interval = self.cfg.poll_interval_ms / 1000.0
        while time.monotonic() < deadline:
            state = self._evaluate(JS_STATE)
            if state and state.get("found") and state.get("hasCopy") and not state.get("stopActive"):
                return
            time.sleep(interval)
        raise CopyError("Timed out waiting for ChatGPT to finish generating a reply.")

    def copy_latest_reply(self) -> str:
        content = self._evaluate(JS_GET_REPLY)
        if not (content or "").strip():
            raise CopyError("ChatGPT page returned an empty reply via CDP.")
        return content

    def paste_and_send(self, text: str) -> None:
        ok = self._evaluate(JS_SET_VALUE.replace("__TEXT__", json.dumps(text)))
        if ok != "OK":
            raise SendError(f"Could not set ChatGPT composer text ({ok}).")
        time.sleep(0.3)
        result = self._evaluate(JS_SEND)
        if result in ("NO_TEXTAREA", None):
            raise SendError("Could not send the message to ChatGPT.")
        time.sleep(0.5)
        # give the app a moment to clear the composer
        self._evaluate(JS_CLEAR_COMPOSER)

    def close(self) -> None:
        try:
            if self._ws is not None:
                self._ws.close()
        except Exception:
            pass
