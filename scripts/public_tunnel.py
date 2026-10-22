"""
Keeps the public asset tunnel alive. Quick tunnels (trycloudflare.com) get dropped by Cloudflare
after sleep or network changes ("Tunnel not found") and come back on a new random hostname, which
breaks Instagram publishing (Meta error 9004). This supervisor:

  1. starts scripts/asset_tunnel_proxy.py if nothing is listening on the proxy port
  2. starts cloudflared and waits for its https URL
  3. writes that URL to PUBLIC_ASSET_BASE_URL / META_REDIRECT_BASE_URL in .env
  4. touches apps/api/app/main.py so a `uvicorn --reload` API re-reads .env
  5. restarts the tunnel (back to step 2) when cloudflared exits or reports the tunnel is gone

    .venv/bin/python scripts/public_tunnel.py

Note: the API loads .env with override=False, so don't export PUBLIC_ASSET_BASE_URL in the
shell that runs the API. Meta's OAuth redirect URI must also be updated if you reconnect Meta.
"""
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
RELOAD_TOUCH = ROOT / "apps/api/app/main.py"
CLOUDFLARED = os.getenv("CLOUDFLARED", str(ROOT / ".tools/cloudflared"))
PROXY_PORT = int(os.getenv("ASSET_PROXY_PORT", "8090"))
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
DEAD_MARKERS = ("Tunnel not found", "failed to unmarshal quick Tunnel")
ENV_KEYS = ("PUBLIC_ASSET_BASE_URL", "META_REDIRECT_BASE_URL")


def log(msg: str) -> None:
    print(f"[tunnel {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_proxy() -> None:
    if port_open(PROXY_PORT):
        return
    log(f"starting asset proxy on :{PROXY_PORT}")
    subprocess.Popen([sys.executable, str(ROOT / "scripts/asset_tunnel_proxy.py")], cwd=ROOT)
    for _ in range(20):
        if port_open(PROXY_PORT):
            return
        time.sleep(0.5)
    raise SystemExit("asset proxy did not start")


def write_env(url: str) -> None:
    text = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for key in ENV_KEYS:
        line = f"{key}={url}"
        if re.search(rf"^{key}=.*$", text, flags=re.M):
            text = re.sub(rf"^{key}=.*$", line, text, flags=re.M)
        else:
            text = text.rstrip("\n") + f"\n{line}\n"
    ENV_FILE.write_text(text)
    RELOAD_TOUCH.touch()
    log(f".env updated -> {url} (API reload triggered)")


def run_tunnel() -> None:
    proc = subprocess.Popen(
        [CLOUDFLARED, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{PROXY_PORT}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    url, published = None, False
    try:
        for line in proc.stdout:
            if url is None and (m := URL_RE.search(line)):
                url = m.group(0)
            if url and not published and "Registered tunnel connection" in line:
                write_env(url)
                published = True
            if any(marker in line for marker in DEAD_MARKERS):
                log("Cloudflare dropped the tunnel; restarting")
                break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    while True:
        ensure_proxy()
        run_tunnel()
        time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
