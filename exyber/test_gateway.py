import asyncio
import json
import unittest

from exyber.gateway import CAPABILITY, Grant, MAX_BYTES, MockGateway


def request(**changes):
    fields = {"version": 1, "request_id": "req-1", "capability": CAPABILITY,
              "args": {}, "timeout_ms": 100}
    fields.update(changes)
    return json.dumps(fields).encode()


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.gateway = MockGateway([Grant("alice", CAPABILITY, 101)], clock=lambda: 100)

    async def test_status_and_audit(self):
        response = await self.gateway.handle("alice", request())
        self.assertEqual(response, {"version": 1, "request_id": "req-1", "ok": True,
                                    "result": {"state": "synthetic-ok"}})
        self.assertEqual(self.gateway.audit, [{"principal": "alice", "request_id": "req-1",
                                               "outcome": "ok"}])

    async def test_unknown_capability_is_not_dispatched(self):
        response = await self.gateway.handle("alice", request(capability="device.control"))
        self.assertEqual(response["error"], "unknown_capability")
        self.assertEqual(self.gateway.audit[-1]["outcome"], "unknown_capability")

    async def test_invalid_and_oversized_inputs_do_not_consume_id(self):
        bad = [b"\xff", b"{", b" " * (MAX_BYTES + 1),
               b'{"version":1,"version":1}', request(version=True),
               b'[' * 1000 + b']' * 1000,
               request(args={"payload": "secret"}), request(timeout_ms=0),
               request(request_id="bad id"), request(extra=1)]
        for raw in bad:
            with self.subTest(raw=raw[:40]):
                response = await self.gateway.handle("alice", raw)
                self.assertEqual(response["error"], "invalid_request")
                self.assertIsNone(response["request_id"])
                self.assertEqual(self.gateway.audit[-1], {"principal": "alice",
                    "request_id": None, "outcome": "invalid_request"})
        self.assertTrue((await self.gateway.handle("alice", request()))["ok"])
        self.assertNotIn("secret", repr(self.gateway.audit))

    async def test_unknown_capability_consumes_id(self):
        await self.gateway.handle("alice", request(capability="other"))
        self.assertEqual((await self.gateway.handle("alice", request()))["error"], "replay")

    async def test_grants_are_scoped_revocable_and_expire_at_boundary(self):
        for grant in [Grant("alice", CAPABILITY, 101, revoked=True),
                      Grant("alice", CAPABILITY, 100), Grant("bob", CAPABILITY, 101),
                      Grant("alice", "other", 101)]:
            with self.subTest(grant=grant):
                gateway = MockGateway([grant], clock=lambda: 100)
                self.assertEqual((await gateway.handle("alice", request()))["error"],
                                 "not_authorized")
                self.assertEqual(gateway.audit[-1]["outcome"], "not_authorized")

    async def test_replay_scoped_to_principal_and_denials_consume_id(self):
        self.assertEqual((await self.gateway.handle("bob", request()))["error"],
                         "not_authorized")
        self.assertEqual((await self.gateway.handle("bob", request()))["error"], "replay")
        self.assertTrue((await self.gateway.handle("alice", request()))["ok"])
        self.assertEqual((await self.gateway.handle("alice", request()))["error"], "replay")
        self.assertEqual(self.gateway.audit[-1]["outcome"], "replay")

    async def test_timeout_is_audited_and_consumes_id(self):
        cancelled = asyncio.Event()

        async def slow():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        gateway = MockGateway([Grant("alice", CAPABILITY, 101)], lambda: 100, slow)
        self.assertEqual((await gateway.handle("alice", request(timeout_ms=1)))["error"],
                         "timeout")
        self.assertTrue(cancelled.is_set())
        self.assertEqual(gateway.audit[-1]["outcome"], "timeout")
        self.assertEqual((await gateway.handle("alice", request()))["error"], "replay")

    async def test_failure_does_not_expose_exception_and_is_audited(self):
        async def failed():
            raise RuntimeError("private details")

        gateway = MockGateway([Grant("alice", CAPABILITY, 101)], lambda: 100, failed)
        response = await gateway.handle("alice", request())
        self.assertEqual(response["error"], "internal_error")
        self.assertEqual(gateway.audit[-1]["outcome"], "internal_error")
        self.assertNotIn("private details", repr((response, gateway.audit)))


if __name__ == "__main__":
    unittest.main()
