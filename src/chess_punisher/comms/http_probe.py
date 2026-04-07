"""Tiny helper for direct HTTP confirmation against an ESP32."""

from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HttpProbeResult:
    status: int
    url: str
    body: str

    def json_body(self) -> dict[str, object]:
        payload = json.loads(self.body)
        if not isinstance(payload, dict):
            raise ValueError("response body must be a JSON object")
        return payload


def health_url_from_punish_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    if path.endswith("/punish"):
        health_path = f"{path[:-7]}/health" or "/health"
    else:
        health_path = "/health"
    return urlunsplit((parts.scheme, parts.netloc, health_path, "", ""))


def build_probe_url(
    url: str,
    severity: str = "TEST",
    loss_cp: int = 0,
    move_uci: str = "e2e4",
    pulse_ms: int = 150,
) -> str:
    query = urlencode(
        {
            "severity": severity,
            "loss": str(loss_cp),
            "move": move_uci,
            "pulse_ms": str(pulse_ms),
        }
    )
    return f"{url}?{query}"


def fetch_json(url: str, timeout_s: float = 2.0) -> HttpProbeResult:
    req = Request(url, method="GET")
    with urlopen(req, timeout=timeout_s) as response:
        body = response.read().decode("utf-8")
        status = getattr(response, "status", response.getcode())
    return HttpProbeResult(status=status, url=url, body=body)


def send_http_probe(
    url: str,
    severity: str = "TEST",
    loss_cp: int = 0,
    move_uci: str = "e2e4",
    pulse_ms: int = 150,
    timeout_s: float = 2.0,
) -> HttpProbeResult:
    target = build_probe_url(
        url=url,
        severity=severity,
        loss_cp=loss_cp,
        move_uci=move_uci,
        pulse_ms=pulse_ms,
    )
    return fetch_json(target, timeout_s=timeout_s)
