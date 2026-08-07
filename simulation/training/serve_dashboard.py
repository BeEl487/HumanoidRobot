"""Serve a training run's dashboard directory over plain HTTP.

`dashboard.html` polls `manifest.json` via fetch(), which browsers block on file:// URIs (CORS) --
this must be served, even just locally. Usage:

    python serve_dashboard.py training/runs/v12
    # then open http://localhost:8000/dashboard.html

Safe to start before the first checkpoint lands -- the page shows a waiting state until
progress_artifacts.py writes the first manifest.json entry.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import pathlib

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", help="e.g. training/runs/v12")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    run_dir = pathlib.Path(args.run_dir).resolve()
    if not run_dir.exists():
        run_dir.mkdir(parents=True)
        print(f"Created empty {run_dir} -- dashboard will show a waiting state until training starts.")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(run_dir))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"Serving {run_dir} at http://localhost:{args.port}/dashboard.html")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
