# Synthetic contract and boundaries

The intended layering is Exo tool adapter → Exyber request protocol → replaceable transport → device-local policy and capability implementation. Iroh can authenticate a connecting endpoint and protect a connection; Exyber must independently decide who may invoke which capability on which device and under what conditions. No integration between these layers exists yet.

The mock accepts UTF-8 JSON bytes, at most 4096 bytes. Objects must have exactly `version`, `request_id`, `capability`, `args`, and `timeout_ms`. Version is integer `1`; request IDs are 1–64 ASCII letters, digits, underscores or hyphens; capability is a nonempty string of at most 64 characters; `args` is an empty object; timeout is an integer from 1 to 1000 milliseconds. Duplicate JSON keys are invalid. The only recognized capability is `synthetic.status`, which returns `{"state":"synthetic-ok"}`. A future protocol will need formal negotiation and framing; this model does neither.

Responses contain `version`, `request_id` (null if invalid input), `ok`, and either `result` or a stable `error` code. The caller supplies a fake principal out of band. A matching in-memory grant must identify that principal and capability, be unrevoked, and expire strictly after the injected clock's current time. No key, signature, identity proof or token is implemented.

Error codes are `invalid_request`, `replay`, `unknown_capability`, `not_authorized`, `timeout`, and `internal_error`. The mock validates first, consumes a new ID, checks capability, then checks the grant. Error ordering here is experimental and should be revisited for information disclosure before any network use.

Once a valid request is admitted, its `(principal, request_id)` is consumed even if denied or timed out; reuse gets `replay`. Invalid requests do not consume IDs. Replay state is process-local, unbounded and lost on restart; it is unsuitable for a real service. Timeouts cancel the synthetic coroutine but cannot establish that a real operation stopped. Real actions require explicit idempotency, cancellation and reconciliation semantics.

Each completed attempt records one in-memory audit event containing only principal, parsed request ID if available, and outcome. It deliberately excludes payloads. Invalid inputs have a null request ID; an externally cancelled call may have no event. This is neither durable nor tamper-resistant; a real design must address retention, privacy, failure to write audit records and trusted timestamps. The model has no concurrency guarantees, persistence, rate limiting, wire authentication, key management, transport, per-device pairing, or production authorization.

## Design questions before real devices

- Bind authenticated transport identities to device-owner-approved, scoped and expiring grants; design revocation and recovery independently of discovery.
- Define device-local approval and visible audit, including consequences of offline/revoked peers, lost keys and reconnects.
- Specify resource limits, durable replay and request identity, timeouts, operation outcomes and behavior after interruption.
- Choose a relay and metadata/privacy policy; test NAT traversal and degraded connectivity rather than assuming availability. Public development relays are not a production plan.
- Verify Iroh core and official language binding compatibility against exact pinned versions before choosing an integration route. Exo remains a separate consumer; don't couple its tool API to Iroh internals.
