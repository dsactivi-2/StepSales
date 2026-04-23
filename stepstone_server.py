#!/usr/bin/env python3
"""
Minimal MCP-style HTTP server for Stepstone integration.
Uses only Python standard library to work in python:3.11-slim.
"""

import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("stepstone-mcp")


class StepstoneServer:
    """Stepstone job search integration using urllib (no external deps)."""

    def __init__(self, zip_code: str = "40210", radius: int = 15, timeout: int = 10):
        self.zip_code = zip_code
        self.radius = radius
        self.timeout = timeout
        self.headers = {"User-Agent": "Stepsales-MCP/1.0"}

    def search_jobs(self, query: str) -> list:
        """Search Stepstone and return simplified job listings."""
        url = self._build_search_url(query)
        logger.info(f"Searching Stepstone: {query}")
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            jobs = self._parse_jobs(html)
            logger.info(f"Found {len(jobs)} jobs for '{query}'")
            return jobs
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return []

    def _build_search_url(self, term: str) -> str:
        base = "https://www.stepstone.de"
        params = urllib.parse.urlencode({"q": term, "zc": self.zip_code, "r": self.radius})
        return f"{base}/stellenangebote--{urllib.parse.quote(term)}.html?{params}"

    def _parse_jobs(self, html: str) -> list:
        """Basic HTML parser for job listings (no BeautifulSoup)."""
        jobs = []
        # Look for job card patterns in HTML
        # This is a simplified parser - in production use proper HTML parsing
        import re

        # Try to find job titles and links
        title_pattern = re.compile(
            r'<[^>]*class="[^"]*result-list-item__headline[^"]*"[^>]*>'
            r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in title_pattern.finditer(html):
            url = match.group(1)
            title = match.group(2).strip()
            if url.startswith("/"):
                url = "https://www.stepstone.de" + url
            jobs.append({"title": title, "url": url, "company": "", "location": "", "salary": ""})

        return jobs[:10]  # Limit results


stepstone = StepstoneServer()


class MCPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP-style endpoints."""

    def do_GET(self):
        if self.path == "/health" or self.path == "/healthz":
            self._send_json({"status": "healthy", "service": "stepstone-mcp", "timestamp": datetime.now().isoformat()})

        elif self.path == "/" or self.path.startswith("/search"):
            # Extract query from URL
            query = ""
            if "?" in self.path:
                params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                query = params.get("q", params.get("query", [""]))[0]

            if not query:
                self._send_json({"error": "Missing 'q' query parameter", "usage": "/search?q=python+developer"}, status=400)
                return

            jobs = stepstone.search_jobs(query)
            self._send_json({"query": query, "results": len(jobs), "jobs": jobs})

        else:
            self._send_json({"error": f"Unknown path: {self.path}", "endpoints": ["/health", "/search?q=..."]}, status=404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, status=400)
            return

        if self.path == "/search":
            query = payload.get("q", payload.get("query", ""))
            if not query:
                self._send_json({"error": "Missing 'q' field"}, status=400)
                return
            jobs = stepstone.search_jobs(query)
            self._send_json({"query": query, "results": len(jobs), "jobs": jobs})
        else:
            self._send_json({"error": "Unknown POST path"}, status=404)

    def _send_json(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))

    def log_message(self, format, *args):
        logger.info("%s - %s", self.client_address[0], format % args)


def main():
    host = "0.0.0.0"
    port = 8000
    server = HTTPServer((host, port), MCPHandler)
    logger.info(f"Stepstone MCP Server starting on {host}:{port}")
    logger.info(f"  Health:  http://localhost:{port}/health")
    logger.info(f"  Search:  http://localhost:{port}/search?q=python")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
