"""A deliberately synthetic, in-memory request and policy model."""

import asyncio
from dataclasses import dataclass
import json
import re
from typing import Awaitable, Callable

MAX_BYTES = 4096
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
CAPABILITY = "synthetic.status"


@dataclass(frozen=True)
class Grant:
    principal: str
    capability: str
    expires_at: float
    revoked: bool = False


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _parse(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError("invalid input")
    try:
        request = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(request, dict) or set(request) != {
        "version", "request_id", "capability", "args", "timeout_ms"
    }:
        raise ValueError("invalid fields")
    rid, cap, timeout = request["request_id"], request["capability"], request["timeout_ms"]
    if (type(request["version"]) is not int or request["version"] != 1
            or not isinstance(rid, str) or not ID_PATTERN.fullmatch(rid)
            or not isinstance(cap, str) or not 1 <= len(cap) <= 64
            or request["args"] != {} or not isinstance(request["args"], dict)
            or type(timeout) is not int or not 1 <= timeout <= 1000):
        raise ValueError("invalid values")
    return request


async def _status():
    return {"state": "synthetic-ok"}


class MockGateway:
    """Only for single-process synthetic tests; no real trust is established."""

    def __init__(self, grants: list[Grant], clock: Callable[[], float],
                 status: Callable[[], Awaitable[dict]] = _status):
        self.grants = grants
        self.clock = clock
        self.status = status
        self.seen = set()
        self.audit = []

    async def handle(self, principal: str, raw: bytes) -> dict:
        request_id = None

        def finish(error=None, result=None):
            outcome = error or "ok"
            self.audit.append({"principal": principal, "request_id": request_id,
                               "outcome": outcome})
            response = {"version": 1, "request_id": request_id, "ok": error is None}
            response["error" if error else "result"] = error if error else result
            return response

        try:
            request = _parse(raw)
        except ValueError:
            return finish("invalid_request")
        request_id = request["request_id"]
        identity = (principal, request_id)
        if identity in self.seen:
            return finish("replay")
        self.seen.add(identity)
        if request["capability"] != CAPABILITY:
            return finish("unknown_capability")
        if not any(g.principal == principal and g.capability == CAPABILITY
                   and not g.revoked and g.expires_at > self.clock() for g in self.grants):
            return finish("not_authorized")
        try:
            result = await asyncio.wait_for(self.status(), request["timeout_ms"] / 1000)
        except asyncio.TimeoutError:
            return finish("timeout")
        except Exception:
            return finish("internal_error")
        return finish(result=result)
