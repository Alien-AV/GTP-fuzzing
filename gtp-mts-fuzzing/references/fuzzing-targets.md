# Fuzzing Targets

## Goal

Generate malformed or boundary-value GTP messages likely to stress the GW parser that inspects packets crossing the path.

The current focus is parser exposure, not protocol compliance.

## Good Initial Mutation Targets

### Header

- length field mismatches
- sequence number edge values
- TEID edge values
- flags with inconsistent content

### IMSI

- too short
- too long
- odd/even nibble anomalies
- non-decimal content if encoder allows it

### F-TEID

- interface type out of expected range
- TEID zero / max / reused values
- mismatched IPv4 flag and address content
- malformed address length combinations

### Bearer Context

- missing nested mandatory IE
- repeated nested IE
- inconsistent EBI / F-TEID / QoS combinations

### AMBR

- zero
- max integer
- swapped uplink/downlink assumptions

### PAA

- invalid PDN type combinations
- malformed IPv4/IPv6 presence
- inconsistent address family vs payload

## Working Method

1. Keep one known-good baseline.
2. Create a fresh iteration-specific client/server XML pair.
3. Append the iteration summary to `gtp_mts_fuzz_iterations.log`.
4. Mutate one field family at a time.
5. Run server first, delay, then client with `nohup`.
6. Ignore MTS CLI output for interpretation.
7. Compare:
- scenario log decode
- `testPlan.csv`
- GW behavior visible from crash monitoring only
8. Save payload variants that trigger parser crashes, malformed classification, or unexpected acceptance.
9. Replay the baseline every 20 mutations.

## Practical Advice

- Prefer cloning the exact Release13 scenario under a new filename before fuzzing.
- Avoid changing many unrelated fields in one iteration.
- If the decoder still accepts the message, the scenario log gives you the exact serialized structure to compare against baseline.
- Keep the same iteration id on the local ledger, client XML copy, server XML copy, and any GW crash notes.
