# Exyber

Exyber extends Exo's presence in the outside world to other devices. Its aim is to let a digital intelligence interact with devices through explicitly granted capabilities, with the person who owns each device in control. Eventually, selected execution context might move to a device; that is a separate problem from sending requests to it.

The name combines **exo**, evoking the external, with **cyber**, from Greek *kybernan* (κυβερνᾶν), to steer or pilot. The intended image is piloting a ship: Exo reaches the world; Exyber may give it a way to act through devices in that world. Exyber is a coined name, not an ancient Greek word.

This fork retains the upstream [Iroh](../README.md) workspace and its history and licenses. Exyber-specific experiments live here, outside that workspace. Iroh is a candidate replaceable transport: it offers authenticated, encrypted QUIC connections, direct connectivity and relay fallback. An endpoint identity is not a grant of authority. Encryption is not anonymity; network metadata and relay policy matter. No production relay has been selected.

## First slice

`exyber/gateway.py` models a versioned request/response contract and a fake in-memory gateway. Its only capability returns a fixed synthetic status. It has no Iroh, network, real device, credential, filesystem or Exo integration. Grants, identities, clock and audit sink are deliberately artificial. This is an executable design experiment, **not a security boundary or production authorization implementation**.

Run with Python 3.10 or newer, using only the standard library:

```sh
python3 -m unittest discover -s exyber -p 'test_*.py' -v
```

See [contract and architecture](architecture.md) for the exact semantics and limitations.

## Direction

1. Validate a bounded contract and policy behavior with synthetic devices (this slice).
2. Design pairing, scoped grants, revocation, local confirmation, bounded replay protection and durable audit with threat modeling and review. Decide the relay, availability and privacy model.
3. Separately prototype an Iroh transport between test endpoints and verify actual binding/version compatibility with Exo's Python runtime. Keep Exo's tool adapter separate from transport and device policy.
4. With explicit device-owner authorization, explore a narrow read-only capability on real devices, then carefully scoped actions. Each capability needs its own consent, containment and failure semantics.
5. Explore moving selected execution state independently; Iroh does not migrate processes or agent identity. Physical devices and robotics require device-local safety controls and a separate safety design.

No generic remote shell, unrestricted control, persistent credentials, real pairing, deployment or agent migration is included here. The roadmap is a set of questions and milestones, not a promise of safe or available capabilities.
