import base64
import json
import math
import re
from http.server import BaseHTTPRequestHandler
from io import BytesIO
from typing import Dict, Tuple

import matplotlib

# Ensure matplotlib works in headless environments (e.g., serverless)
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


SAFE_FUNCTIONS: Dict[str, object] = {
    "np": np,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "arcsin": np.arcsin,
    "arccos": np.arccos,
    "arctan": np.arctan,
    "sinh": np.sinh,
    "cosh": np.cosh,
    "tanh": np.tanh,
    "exp": np.exp,
    "log": np.log,
    "log10": np.log10,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "pi": math.pi,
    "e": math.e,
}

DEFAULT_PAYLOAD = {
    "expression": "sin(2 * pi * x)",
    "xMin": -2 * math.pi,
    "xMax": 2 * math.pi,
    "samples": 500,
    "title": "Courbe paramétrable",
    "xLabel": "x",
    "yLabel": "f(x)",
    "color": "#2563eb",
    "lineWidth": 2.0,
    "grid": True,
    "marker": "",
}


def parse_payload(body: str) -> Dict[str, object]:
    if not body:
        return dict(DEFAULT_PAYLOAD)

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Requête illisible (JSON invalide): {exc}") from exc

    payload = dict(DEFAULT_PAYLOAD)
    payload.update({k: v for k, v in data.items() if v is not None})
    return payload


def validate_payload(payload: Dict[str, object]) -> Dict[str, object]:
    try:
        x_min = float(payload["xMin"])
        x_max = float(payload["xMax"])
        if x_min >= x_max:
            raise ValueError
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Intervalle invalide: xMin doit être < xMax") from exc

    try:
        samples = int(payload["samples"])
        if not 2 <= samples <= 10_000:
            raise ValueError
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Le nombre d'échantillons doit être entre 2 et 10000") from exc

    expression = str(payload["expression"]).strip()
    if not expression:
        raise ValueError("L'expression ne peut pas être vide.")

    if re.search(r"__|import|\bexec\b|\beval\b|\bos\b|\bsys\b", expression):
        raise ValueError("L'expression contient des éléments non autorisés.")

    payload["xMin"] = x_min
    payload["xMax"] = x_max
    payload["samples"] = samples
    payload["expression"] = expression
    payload["title"] = str(payload.get("title", "")).strip() or DEFAULT_PAYLOAD["title"]
    payload["xLabel"] = str(payload.get("xLabel", "")).strip() or DEFAULT_PAYLOAD["xLabel"]
    payload["yLabel"] = str(payload.get("yLabel", "")).strip() or DEFAULT_PAYLOAD["yLabel"]
    payload["color"] = str(payload.get("color") or DEFAULT_PAYLOAD["color"])
    payload["marker"] = str(payload.get("marker") or "")

    try:
        line_width = float(payload["lineWidth"])
        if not 0.1 <= line_width <= 10:
            raise ValueError
    except Exception as exc:  # noqa: BLE001
        raise ValueError("L'épaisseur de ligne doit être entre 0.1 et 10.") from exc

    payload["lineWidth"] = line_width
    payload["grid"] = bool(payload.get("grid", DEFAULT_PAYLOAD["grid"]))
    return payload


def evaluate_expression(expression: str, x: np.ndarray) -> np.ndarray:
    safe_locals = dict(SAFE_FUNCTIONS)
    safe_locals["x"] = x
    try:
        result = eval(expression, {"__builtins__": {}}, safe_locals)  # noqa: S307
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Impossible d'évaluer l'expression: {exc}") from exc

    if not isinstance(result, np.ndarray):
        result = np.array(result, dtype=float)
    if result.shape != x.shape:
        raise ValueError("L'expression doit produire une valeur pour chaque point x.")
    if not np.isfinite(result).all():
        raise ValueError("L'expression génère des valeurs non finies.")
    return result


def render_plot(payload: Dict[str, object]) -> Tuple[str, Dict[str, object]]:
    x = np.linspace(payload["xMin"], payload["xMax"], payload["samples"])
    y = evaluate_expression(payload["expression"], x)

    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=150)
    ax.plot(
        x,
        y,
        color=payload["color"],
        linewidth=payload["lineWidth"],
        marker=payload["marker"] or None,
    )
    ax.set_title(payload["title"])
    ax.set_xlabel(payload["xLabel"])
    ax.set_ylabel(payload["yLabel"])

    if payload["grid"]:
        ax.grid(True, linestyle="--", alpha=0.4)

    fig.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    metadata = {
        "xMin": payload["xMin"],
        "xMax": payload["xMax"],
        "samples": payload["samples"],
    }
    return encoded, metadata


def build_response(status: int, body: Dict[str, object]) -> Tuple[int, Dict[str, str], bytes]:
    json_body = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    return status, headers, json_body


class handler(BaseHTTPRequestHandler):
    max_message_len = 1_000_000

    def do_OPTIONS(self) -> None:  # noqa: N802
        status, headers, body = build_response(200, {})
        self._send(status, headers, body)

    def do_GET(self) -> None:  # noqa: N802
        encoded, metadata = render_plot(DEFAULT_PAYLOAD)
        body = {"image": f"data:image/png;base64,{encoded}", "metadata": metadata, "default": True}
        status, headers, payload = build_response(200, body)
        self._send(status, headers, payload)

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length") or "0")
        if content_length > self.max_message_len:
            status, headers, payload = build_response(
                413,
                {"error": "Payload trop volumineux."},
            )
            self._send(status, headers, payload)
            return

        body_bytes = self.rfile.read(content_length) if content_length else b""
        body = body_bytes.decode("utf-8")

        try:
            payload = parse_payload(body)
            payload = validate_payload(payload)
            encoded, metadata = render_plot(payload)
            response_body = {
                "image": f"data:image/png;base64,{encoded}",
                "metadata": metadata,
                "default": False,
            }
            status, headers, payload_bytes = build_response(200, response_body)
        except ValueError as exc:
            status, headers, payload_bytes = build_response(400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            status, headers, payload_bytes = build_response(500, {"error": f"Erreur interne: {exc}"})

        self._send(status, headers, payload_bytes)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        # Silence default logging to avoid polluting serverless logs.
        return

    def _send(self, status: int, headers: Dict[str, str], body: bytes) -> None:
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)


if __name__ == "__main__":
    from socketserver import TCPServer

    host = "127.0.0.1"
    port = 8001

    with TCPServer((host, port), handler) as httpd:
        print(f"Serveur local disponible sur http://{host}:{port}")  # noqa: T201
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:  # pragma: no cover - manual stop
            print("\nArrêt du serveur.")  # noqa: T201
