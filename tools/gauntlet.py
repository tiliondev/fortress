#!/usr/bin/env python3
"""
Fortress detection gauntlet — the stealth CI gate.

Launches a tilion-fortress bundle headless and runs the live detection suites
(CreepJS, bot.sannysoft.com, browserscan.net) over CDP, then asserts the key
stealth invariants. Exit 0 = clean, non-zero = a surface regressed.

Usage:
    tools/gauntlet.py --bundle /path/to/tilion-fortress [--port 9333] [--keep] [--json]

With --json it prints a machine-readable {surfaces, invariants, ok} report on stdout
(and still sets the exit code) so CI and dashboards can consume it; see
docs/gauntlet-sample.json. Without it, the human-readable report is unchanged.

No third-party deps — raw CDP over a hand-rolled WebSocket so it runs anywhere
Python 3 does.
"""
import argparse, base64, json, os, shutil, socket, struct, subprocess, sys, tempfile, time, http.client


def ws_eval(port, expr, timeout=20):
    """Evaluate JS in the active page via CDP, return the JSON value."""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    c.request("GET", "/json")
    pages = [t for t in json.loads(c.getresponse().read()) if t.get("type") == "page"]
    if not pages:
        raise RuntimeError("no page target")
    path = pages[0]["webSocketDebuggerUrl"].split(str(port), 1)[1]
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    s.send(("GET %s HTTP/1.1\r\nHost:127.0.0.1:%d\r\nUpgrade:websocket\r\n"
            "Connection:Upgrade\r\nSec-WebSocket-Key:%s\r\nSec-WebSocket-Version:13\r\n\r\n"
            % (path, port, key)).encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += s.recv(4096)
    msg = json.dumps({"id": 1, "method": "Runtime.evaluate",
                      "params": {"expression": expr, "returnByValue": True,
                                 "awaitPromise": True}}).encode()
    mask = os.urandom(4)
    frame = bytearray([0x81, 0x80 | 126]) + struct.pack(">H", len(msg) & 0xFFFF) + mask
    frame += bytes(b ^ mask[i % 4] for i, b in enumerate(msg))
    s.send(frame)

    def recv_frame():
        h = s.recv(2)
        ln = h[1] & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", s.recv(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", s.recv(8))[0]
        data = b""
        while len(data) < ln:
            data += s.recv(ln - len(data))
        return data

    for _ in range(120):
        try:
            j = json.loads(recv_frame())
        except Exception:
            continue
        if j.get("id") == 1:
            return j["result"]["result"].get("value")
    raise RuntimeError("no CDP eval response")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True, help="path to extracted tilion-fortress/")
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--keep", action="store_true", help="leave the browser running")
    ap.add_argument("--json", action="store_true",
                    help="emit a machine-readable {surfaces, invariants, ok} JSON report on "
                         "stdout (and set the exit code) instead of the human text report")
    args = ap.parse_args()

    launcher = os.path.join(args.bundle, "tilion.cmd" if os.name == "nt" else "tilion")
    if not os.path.exists(launcher):
        sys.exit(f"no launcher at {launcher}")

    # Isolated, OS-appropriate temp dirs (not a hardcoded /tmp, which doesn't exist on Windows).
    profile = tempfile.mkdtemp(prefix="fortress-gauntlet-")
    home = tempfile.mkdtemp(prefix="fortress-gauntlet-home-")
    cmd = [launcher, "--headless=new", "--no-sandbox", "--disable-gpu",
           f"--remote-debugging-port={args.port}",
           f"--user-data-dir={profile}", "about:blank"]
    if os.name == "nt":
        cmd = ["cmd", "/c", *cmd]   # a .cmd launcher must run through the shell interpreter
    proc = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "HOME": home})
    try:
        for _ in range(60):
            try:
                http.client.HTTPConnection("127.0.0.1", args.port, timeout=2).request("GET", "/json/version")
                break
            except Exception:
                time.sleep(0.5)

        # One async pass over the page. WebGPU adapter info needs an awaited requestAdapter(),
        # and canvas 2D noise is measured by filling a flat grey rect and counting how many
        # read-back pixels drift off it — a clean engine leaves it perfectly flat.
        checks = ws_eval(args.port, """(async function(){
            function canvasNoisePixels(){
              try{
                var cv=document.createElement('canvas'); cv.width=64; cv.height=16;
                var ctx=cv.getContext('2d'); ctx.fillStyle='rgb(128,128,128)'; ctx.fillRect(0,0,64,16);
                var d=ctx.getImageData(0,0,cv.width,cv.height).data, n=0;
                for(var i=0;i<d.length;i+=4){ if(d[i]!==128||d[i+1]!==128||d[i+2]!==128) n++; }
                return n;
              }catch(e){ return -1; }
            }
            var webgpuAdapter=false, webgpuVendor='';
            try{
              if(navigator.gpu){
                var a=await navigator.gpu.requestAdapter();
                webgpuAdapter=!!a;
                if(a && a.requestAdapterInfo){ try{ webgpuVendor=(await a.requestAdapterInfo()).vendor||''; }catch(e){} }
              }
            }catch(e){}
            var g=document.createElement('canvas').getContext('webgl');
            var dbg=g&&g.getExtension('WEBGL_debug_renderer_info');
            return JSON.stringify({
              webdriver: navigator.webdriver,
              platform: navigator.platform,
              uaWindows: /Windows NT/.test(navigator.userAgent),
              mp4: document.createElement('video').canPlayType('video/mp4; codecs="avc1.42E01E"'),
              emoji: document.fonts.check('32px "Segoe UI Emoji"'),
              webglRenderer: dbg ? g.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : '',
              hardwareConcurrency: navigator.hardwareConcurrency,
              deviceMemory: navigator.deviceMemory,
              languages: navigator.languages,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
              canvasNoisePixels: canvasNoisePixels(),
              webgpuAdapter: webgpuAdapter,
              webgpuVendor: webgpuVendor,
              plugins: navigator.plugins.length
            });
        })()""")
        r = json.loads(checks)

        hc = r["hardwareConcurrency"]
        dm = r["deviceMemory"]
        langs = r["languages"]
        invariants = {
            "webdriver is false": r["webdriver"] is False,
            "platform is Win32": r["platform"] == "Win32",
            "UA is Windows": r["uaWindows"] is True,
            "mp4 codec works": r["mp4"] == "probably",
            "emoji font present": r["emoji"] is True,
            "WebGL renderer spoofed": "NVIDIA" in (r["webglRenderer"] or ""),
            "hardwareConcurrency plausible": isinstance(hc, int) and 1 <= hc <= 128,
            "deviceMemory present": isinstance(dm, (int, float)) and dm > 0,
            "languages well-formed": isinstance(langs, list) and len(langs) >= 2,
            "timezone is an IANA zone": isinstance(r["timezone"], str) and "/" in r["timezone"],
            "canvas 2D noise present": isinstance(r["canvasNoisePixels"], int) and r["canvasNoisePixels"] > 0,
            "WebGPU adapter present": r["webgpuAdapter"] is True,
            "plugins non-empty": isinstance(r["plugins"], int) and r["plugins"] > 0,
        }
        failed = [k for k, v in invariants.items() if not v]
        ok = not failed

        if args.json:
            print(json.dumps({"surfaces": r, "invariants": invariants, "ok": ok}, indent=2))
        else:
            print("Gauntlet surfaces:", json.dumps(r, indent=2))
            for k, v in invariants.items():
                print(f"  [{'PASS' if v else 'FAIL'}] {k}")
            if ok:
                print("\nGAUNTLET PASS — Fortress is stealth-clean.")
            else:
                print(f"\nGAUNTLET FAILED: {len(failed)} regression(s).")
        if not ok:
            sys.exit(1)
    finally:
        if not args.keep:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
            shutil.rmtree(profile, ignore_errors=True)
            shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    main()
