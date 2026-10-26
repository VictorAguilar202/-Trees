"""Local web application for an archaeological timber decision tree."""

from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8000


@dataclass(frozen=True)
class DecisionNode:
    node_id: str
    title: str
    prompt: str | None = None
    yes: "DecisionNode | None" = None
    no: "DecisionNode | None" = None
    recommendation: str | None = None
    rationale: str | None = None

    @property
    def is_leaf(self) -> bool:
        return self.recommendation is not None


DECISION_TREE = DecisionNode(
    node_id="root",
    title="Current storage condition",
    prompt="Is the timber still submerged or kept continuously wet?",
    yes=DecisionNode(
        node_id="wet-condition",
        title="Condition while wet",
        prompt="Do you observe active surface softening or unusual growth?",
        yes=DecisionNode(
            node_id="wet-urgent",
            title="Prioritize specialist assessment",
            recommendation=(
                "Keep the timber wet and arrange prompt assessment by a "
                "trained archaeological conservator."
            ),
            rationale=(
                "The combination of continuous moisture and visible change "
                "could indicate instability. Avoid cleaning or drying it."
            ),
        ),
        no=DecisionNode(
            node_id="wet-stable",
            title="Maintain stable wet storage",
            recommendation=(
                "Keep the timber submerged in its current documented "
                "environment while arranging a professional condition review."
            ),
            rationale=(
                "A stable wet environment can reduce sudden moisture changes "
                "while the object awaits specialist assessment."
            ),
        ),
    ),
    no=DecisionNode(
        node_id="dry-condition",
        title="Condition while not submerged",
        prompt="Is the timber visibly cracked, warped, or powdery?",
        yes=DecisionNode(
            node_id="dry-urgent",
            title="Limit handling and seek advice",
            recommendation=(
                "Limit handling, support the object, and contact an "
                "archaeological conservator before changing its environment."
            ),
            rationale=(
                "Visible damage can make handling or rapid humidity changes "
                "risky. This guide cannot diagnose the cause."
            ),
        ),
        no=DecisionNode(
            node_id="dry-documentation",
            title="Check the archaeological record",
            prompt="Is the object's find location and recovery history documented?",
            yes=DecisionNode(
                node_id="documented",
                title="Plan a documented condition review",
                recommendation=(
                    "Preserve the recovery notes and arrange a condition review "
                    "before cleaning, treatment, or display."
                ),
                rationale=(
                    "Known context helps conservators interpret the timber "
                    "and choose appropriate next steps."
                ),
            ),
            no=DecisionNode(
                node_id="undocumented",
                title="Record context before intervention",
                recommendation=(
                    "Record the object's current condition, location, and any "
                    "known recovery details; avoid cleaning it."
                ),
                rationale=(
                    "Even incomplete context can be valuable. Record what is "
                    "known and clearly mark what remains uncertain."
                ),
            ),
        ),
    ),
)


def serialize_node(node: DecisionNode) -> dict[str, Any]:
    """Convert the in-memory tree into JSON-compatible data for the frontend."""
    if node.is_leaf:
        return {
            "id": node.node_id,
            "title": node.title,
            "recommendation": node.recommendation,
            "rationale": node.rationale,
        }
    return {
        "id": node.node_id,
        "title": node.title,
        "prompt": node.prompt,
        "yes": serialize_node(node.yes),  # type: ignore[arg-type]
        "no": serialize_node(node.no),  # type: ignore[arg-type]
    }


def find_node(node: DecisionNode, node_id: str) -> DecisionNode | None:
    if node.node_id == node_id:
        return node
    for child in (node.yes, node.no):
        if child is not None:
            match = find_node(child, node_id)
            if match is not None:
                return match
    return None


class TreeRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filename: str, content_type: str) -> None:
        file_path = ROOT / filename
        try:
            body = file_path.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_file("index.html", "text/html; charset=utf-8")
        elif path == "/styles.css":
            self._send_file("styles.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self._send_file("app.js", "text/javascript; charset=utf-8")
        elif path == "/api/tree":
            self._send_json(serialize_node(DECISION_TREE))
        else:
            self.send_error(404, "Route not found")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/answer":
            self.send_error(404, "Route not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 4096:
                raise ValueError("Request body size is invalid.")
            payload = json.loads(self.rfile.read(length))
            node_id = payload["node_id"]
            answer = payload["answer"]
            if not isinstance(node_id, str) or answer not in ("yes", "no"):
                raise ValueError("Expected a node_id and a yes/no answer.")
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            self._send_json({"error": "Send a valid node_id and yes/no answer."}, 400)
            return

        node = find_node(DECISION_TREE, node_id)
        if node is None or node.is_leaf:
            self._send_json({"error": "That decision node does not exist."}, 404)
            return

        next_node = node.yes if answer == "yes" else node.no
        self._send_json(serialize_node(next_node))  # type: ignore[arg-type]

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), TreeRequestHandler)
    print(f"Serving the timber triage guide at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
