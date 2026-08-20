# -*- coding: utf-8 -*-
"""
원스회화 서버 v1.0
- 같은 폴더의 wons.html을 그대로 서빙 (단일 소스 — py 안에 HTML 내장 없음)
- /api/progress : 기기 간 진행 동기화 (wons_progress.json)
- /sw.js        : 오프라인용 서비스 워커
실행:  python wons_server.py   →  PC: http://localhost:8378
                                     폰: 같은 Wi-Fi에서 http://<PC IP>:8378
"""
import json
import os
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8379
BASE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE, "wons.html")
PROG_PATH = os.path.join(BASE, "wons_progress.json")

SW_JS = """
const C='wonshw-v1';
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.add('/')));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(u.pathname.startsWith('/api/'))return;               // 동기화는 항상 네트워크
  e.respondWith(
    fetch(e.request).then(r=>{                            // 네트워크 우선, 성공 시 캐시 갱신
      if(e.request.method==='GET'&&r.ok){const cp=r.clone();caches.open(C).then(c=>c.put(e.request,cp));}
      return r;
    }).catch(()=>caches.match(e.request).then(m=>m||caches.match('/')))
  );
});
""".strip()


AI_MODEL = "claude-haiku-4-5-20251001"

def ai_check(meaning, target, answer, lang_note):
    """예시와 다른 문장도 문법·의미가 맞으면 정답 처리 (ANTHROPIC_API_KEY 필요)"""
    import urllib.request
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return {"ok": None, "why": "no_key"}
    sys_p = (
        "You grade a beginner English learner's sentence. Given the intended meaning, "
        "a target example sentence, and the student's answer, decide if the student's answer is a "
        "grammatically correct, natural English sentence expressing the same meaning. "
        "It does NOT need to match the example. Minor punctuation/capitalization issues are fine. "
        'Reply ONLY with JSON: {"ok":true|false,"why":"..."} where why is a very short reason in '
        + lang_note + " (about 10 characters)."
    )
    body = json.dumps({
        "model": AI_MODEL, "max_tokens": 150, "system": sys_p,
        "messages": [{"role": "user", "content": f"meaning: {meaning}\nexample: {target}\nstudent: {answer}"}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=9) as r:
            res = json.loads(r.read().decode("utf-8"))
        txt = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
        txt = txt.replace("```json", "").replace("```", "").strip()
        j = json.loads(txt)
        return {"ok": bool(j.get("ok")), "why": str(j.get("why", ""))[:60]}
    except Exception:
        return {"ok": None, "why": "error"}


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class H(BaseHTTPRequestHandler):
    def _hdr(self, code=200, ctype="text/html; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()

    def do_OPTIONS(self):
        self._hdr(204)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html", "/wons.html"):
            if not os.path.exists(HTML_PATH):
                self._hdr(500)
                self.wfile.write(
                    "wons.html 파일이 없습니다. 서버와 같은 폴더에 두세요.".encode("utf-8")
                )
                return
            with open(HTML_PATH, "rb") as f:
                body = f.read()
            self._hdr(200, "text/html; charset=utf-8")
            self.wfile.write(body)
        elif path == "/sw.js":
            self._hdr(200, "application/javascript; charset=utf-8")
            self.wfile.write(SW_JS.encode("utf-8"))
        elif path == "/api/progress":
            if os.path.exists(PROG_PATH):
                with open(PROG_PATH, "r", encoding="utf-8") as f:
                    body = f.read()
            else:
                body = "{}"
            self._hdr(200, "application/json; charset=utf-8")
            self.wfile.write(body.encode("utf-8"))
        else:
            self._hdr(404, "text/plain; charset=utf-8")
            self.wfile.write(b"not found")

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/check":
            try:
                n = int(self.headers.get("Content-Length", 0))
                d = json.loads(self.rfile.read(n).decode("utf-8"))
                out = ai_check(d.get("meaning", ""), d.get("target", ""), d.get("answer", ""), "Simplified Chinese")
            except Exception as e:
                out = {"ok": None, "why": "bad_request"}
            self._hdr(200, "application/json; charset=utf-8")
            self.wfile.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))
            return
        if path != "/api/progress":
            self._hdr(404, "text/plain; charset=utf-8")
            self.wfile.write(b"not found")
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n).decode("utf-8")
            data = json.loads(raw)  # 유효성 확인
            # 서버 데이터가 더 최신이면 덮어쓰지 않음 (오래된 기기가 진행을 지우는 사고 방지)
            if os.path.exists(PROG_PATH):
                try:
                    with open(PROG_PATH, "r", encoding="utf-8") as f:
                        old = json.load(f)
                    if old.get("saved", 0) > data.get("saved", 0):
                        self._hdr(200, "application/json; charset=utf-8")
                        self.wfile.write(b'{"ok":false,"reason":"server_newer"}')
                        return
                except Exception:
                    pass
            tmp = PROG_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, PROG_PATH)
            self._hdr(200, "application/json; charset=utf-8")
            self.wfile.write(b'{"ok":true}')
        except Exception as e:
            self._hdr(400, "application/json; charset=utf-8")
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # 콘솔 조용히


def main():
    if not os.path.exists(HTML_PATH):
        print("[!] wons.html 이 같은 폴더에 없습니다. 함께 두고 다시 실행하세요.")
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    ip = local_ip()
    print("=" * 46)
    print("  원스회화 — 매일 10분 영어")
    print("=" * 46)
    print(f"  PC   : http://localhost:{PORT}")
    print(f"  폰   : http://{ip}:{PORT}  (같은 Wi-Fi)")
    print("  폰 브라우저에서 열고 '홈 화면에 추가'하면 앱처럼 사용")
    print("  종료 : Ctrl+C")
    print("=" * 46)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
        srv.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()
