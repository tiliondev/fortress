"""CLI: `tilion-fortress` — launch Fortress and print the CDP URL."""
import argparse
import signal
import sys
import time

from . import Fortress, __version__


def main():
    ap = argparse.ArgumentParser(prog="tilion-fortress",
                                 description="Launch the Fortress stealth browser (CDP endpoint).")
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--no-headless", action="store_true")
    ap.add_argument("--version", action="version", version=f"tilion-fortress {__version__}")
    args = ap.parse_args()

    f = Fortress(port=args.port, headless=not args.no_headless).start()
    print(f"Fortress up. CDP: {f.cdp_url}", file=sys.stderr)
    print(f.cdp_url)
    signal.signal(signal.SIGINT, lambda *_: (f.close(), sys.exit(0)))
    try:
        while True:
            time.sleep(3600)
    finally:
        f.close()


if __name__ == "__main__":
    main()
