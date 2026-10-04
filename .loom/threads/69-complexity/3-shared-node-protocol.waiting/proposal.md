# 69/3 — share the node's grammar and replies

**Proposal for Bob; no implementation. 2026-10-05.**

Share the small, deterministic part of the node protocol: argument validation,
the UID verb allowlist, receipt construction and the report schema. Keep real
hardware, simulated hardware and audition engine operations where they are.
Use a common dispatch function with injected operations, plus contract/parity
tests. This removes repeated wire decisions without introducing a node class
hierarchy. Retain both OSC libraries for this pass.

There is drift now. Audition advertises contract 1.21 but omits three report
fields and six UID verbs. The real node accepts malformed assignments rejected
by both tools; malformed sync input can terminate its LAN listener. Fix those
defects in small verified steps before widening the shared code. Matching replies
alone cannot prove correctness: all three accept `enabled 0.5` as `enabled 0`.

**Ruling requested:** approve this narrow extraction and bring audition up to
the existing device-management contract using honest local/no-hardware facts
and existing receipts. No new wire tokens, ports, capabilities or engine model.
Defer library consolidation and the horizon engine redesign.

## What is duplicated today

Source census and executable probe: [analyse_protocol.py](analyse_protocol.py),
captured results: [analysis.json](analysis.json). Source hashes and function
locations are in the capture; counts include comments and blank lines within
function spans. Main checkout only; the Monitor worktree was untouched.

| Surface | Real node | simfleet | audition | Combined |
| --- | ---: | ---: | ---: | ---: |
| Whole file | 2,215 | 1,523 | 1,000 | 4,738 |
| UID dispatch | 57 | 217 | 73 | 347 |
| Report construction | 60 | 38 | 37 | 135 |
| Revision receipt | 15 | 13 | 3 | 31 |
| LAN dispatch, lifecycle dispatch and listings, plus the above | 391 | 586 | 273 | 1,250 |
| UID verbs recognized | 16 | 16 | 10 | — |
| Top-level report fields | 21 | 21 | 18 | — |

The last LOC row is **overlapping responsibility**, not 1,250 identical or
removable lines (26.4% of these files). Even the narrower 513-line
UID/report/revision surface contains different side effects and fact gathering.
Concrete repeated wire declarations are measurable:

- Three independently spelled seven-verb no-argument UID allowlists: 21 names
  where seven suffice; each tool separately adds its argument-bearing branches.
- Three identical hostname regular expressions.
- Sixty top-level report-field declarations for a 21-field schema: 39 repeated
  declarations, with audition missing `performance`, `log`, `wifi`.
- Three assignment parsers: real `apply_assign`, simfleet's inline assignment
  branch, audition `_assignment`. Range, types and malformed geometry differ.
- IO write/reinit invalid-payload shaping is separately spelled in simfleet and
  `io_control.py`; the reinit case below already disagrees.
- Repeated audio-config receipt dictionaries in the two tools and real-node
  receipt construction; repeated hostname/enabled/group/revision envelopes;
  repeated patch-list row construction, with different inclusion policies.

This is not three wholly separate protocols anymore. All three reuse
`groups`, `manifest` identities, `paramgen`, `pointfield`, `audio_config`,
`identity`, and `osc_contract.VERSION`. Real node and audition reuse `relay`;
simfleet's parameter/provided-term branch remains separate. Real node and
simfleet reuse `wifi_config`, `log_config`, `performance_mode` and IO stream
`Lease`; simfleet uses `io_protocol` directly, the real node through `IOControl`.
Audition has no Performance, Wi-Fi, logging or IO-control implementation.
simfleet and audition are independent programs, not subclasses of one another.

The old instruction's `LegacyProtocol` docstring example is obsolete: simfleet
now describes `ContractProtocol`. Its current docstring still says no value
streaming, although `stream_io` does emit fake leased values. Do not count old
description drift as evidence that the implementation is absent.

## Direct parity evidence

The probe feeds **identical OSC bytes** into `handle_lan_datagram`,
`receive_contract` and `AuditionRig.relay`. It constructs fixtures without
opening sockets or starting engines. It substitutes successful persistence and
mixer operations, unavailable Wi-Fi hardware, no-bus scan completion, inline
worker execution, and inert timers. It executes actual validators and reply
builders. Assignment engine sends/heartbeat scheduling are suppressed to inspect
assignment admission/state. See the script for every substitution.

32 datagrams were sampled. Thirteen have matching replies across all three,
including silent rejection cases and malformed assignments whose **state differs**.
This is a sample, not coverage of all protocol behavior. JSON is parsed before
comparison; OSC tags, reply address and destination are retained. Report values
such as patch, uptime and revision genuinely differ by host and were not silently
normalized into agreement. The report *schema* differences are the actionable
finding. Real-node/simfleet non-report replies match in 27 of 30 cases without
an exception; the three differences are reinit shaping, sync input handling
and double-token ping reply tags.

| Input / observation | Real node | simfleet | audition |
| --- | --- | --- | --- |
| UID `report` | 21 fields, `,s` | Same 21 fields, `,s` | 18 fields; no `performance`, `log`, `wifi` |
| `io-scan`, no bus | `{bus:null, scanned:true, addresses:[], modules:{}}` | Same | No reply |
| Invalid `io-write`, invalid `io-reinit`, invalid `io-stream` | Existing `err` receipt, expected JSON and `,sss` | Same | No reply |
| Performance refusal of write/stream/Wi-Fi | Existing receipt with `performance` | Same | No reply; no device-side mode |
| `/all/os/performance 1` | Mode true, confirming report | Same behavior, host-specific facts | Ignored; no confirmation |
| Invalid `log-config` | `err` with complete log object | Same | No reply |
| Wi-Fi on unmanaged host | `err unavailable {managed:false}` | Same | No reply |
| `/all/os/ping` string and float tokens | Echo original token/tag and UID | Same | No reply |
| Ping token `.5` explicitly tagged OSC double `d` | Pong retains `,ds` | Pong reconstructs token as float `,fs` | No reply |
| Probe held `id` | `/os/probe 0 id 0`, `,isi` | Same | No reply |
| `/all/os/to uid io-reinit adc extra` | `err {name:"bridge",error:"invalid-arguments"}` | `err {name:"adc",error:"invalid-arguments"}` | No reply |
| Assign id `3.5`, string `"3"`, or id `3` with odd coordinate count | Changes id to 3; invalid geometry becomes empty | Rejects, id stays 0 | Rejects, id stays 0 |
| Valid assignment id 3, position `(1,2)` | Same id and element state | Same | Same |
| `/sync/ping "bad" "123"` | Escapes with `ValueError` | Rejects | No sync handler |
| `enabled 0.5` (OSC float) | Applies 0 and sends success | Same | Same |

The sync exception is more than a reply mismatch: `lan_listener_loop` catches
only `OSError`. An uncaught `ValueError` exits that thread; this is a source-based
inference, not a live-node failure experiment. Repair it before extraction.

The six UID verbs absent from audition are `log-config`, `wifi-config`,
`io-scan`, `io-write`, `io-reinit`, `io-stream`. Missing hardware can be an honest
report/refusal; silently missing a promised receipt is a protocol distinction
that must either be removed or explicitly ratified. Audition's local listener,
editor-element messages, matrix generation and zero-clock event scheduling are
intentional execution adaptations; do not make those identical to a Pi.

Additional executable manifest check: a manifest with an existing inert
`main.scd` entrypoint and `params:[{name:"gain",kind:"not-a-kind"}]` is rejected
by `manifest.load` and audition `_load_patch`. simfleet `load_manifest` accepts it
and declares `gain`. It checks identity qualification but bypasses full schema
validation. Reuse `manifest.load` while retaining verbatim raw text for `/os/params`.

Source inspection also finds that real patch listings retain installed invalid
manifests as `manifest:false`; audition filters them out. simfleet can retain
invalid entries, but its initial `demo-pd` flag uses the weaker loader. The row
format is shared policy; discovery of installed directories versus simulated
snapshots is an adapter concern. A common-fixture listing test is needed before
changing inclusion policy; it was not exercised by this quick datagram probe.

## Smallest useful shared boundary

Use one flat `python/node_protocol.py`, importing the existing domain helpers.
Do not create a second implementation of their validators. Keep
`osc_contract.py` as the version source. No inheritance, registry framework,
transport ownership, new persistent model or generic effect interpreter.

1. **Pure grammar.** Shared assignment validation, sync argument validation,
   UID envelope/allowlist and verb-specific arity/type checks. Preserve OSC type
   information where it matters: ping echoes its original tag, IO stream accepts
   integer 0/1, event elements are floats, timestamps remain strings. Keep
   selector matching in `groups` and parameter grammar in `paramgen`. Input
   adapters provide `(address, tags, values)`, preserving tags rather than only
   inferring them again from decoded Python values.
2. **Pure replies.** Helpers return `(address, values, tags)` using existing
   shapes; each transport encodes and sends them. Centralize report construction
   from adapter-supplied facts, enabled/hostname/audio/log/Wi-Fi/IO/revision
   receipts and listing rows. Require the full report schema rather than quietly
   defaulting an omitted field. Values are still supplied honestly by each host.
3. **One UID dispatcher.** A small verb table specifies allowed envelope,
   argument policy and operation callback; existing `performance_mode` owns its
   gate. Dispatch returns handled/rejected or calls the injected operation. The
   common helper builds its terminal receipt from the operation result. For
   deferred IO work, `IOControl` keeps the completion/FIFO ownership and uses the
   common reply builder when its bridge receipt arrives.

Adapters supply a few wire facts (`uid`, Performance state, update model) and
named operation callables. They continue to own threading, lifecycle ordering,
filesystem observations, reboot, hostname helper, mixer, engine routing, network
configuration and simulated failure/delay. Iterate/filter devices before shared
dispatch: loss injection and UID multiplexing belong to simfleet, not the parser.
Assert at adapter initialization/tests that the verb table has a binding for
every required verb. Adding a verb then exposes missing tool bindings immediately.
No silent generic "unsupported" reply and no new refusal vocabulary.

For audition, bind existing-contract operations to local behavior: unmanaged
Wi-Fi with its existing `unavailable` receipt; no-bus IO with declared missing
modules and existing IO reasons; complete log/Performance facts; retain safe
ephemeral lifecycle operations. Persist Performance on change independently of
the ephemeral engine store, as already required. Never apply laptop power or
network changes to imitate a Pi. Keep any real laptop IO adapter separate from
the shared protocol decision.

Do **not** remove the development checks at effect execution time. A shared
admission check cannot replace `IOControl`'s queued-write recheck or the checks
inside asynchronous fetch/config work. Shared grammar also must not turn
completion-dependent receipts into acknowledgements of mere admission.

This centralizes stable wire decisions, not every LAN branch in one move. Route
the remaining report/list/assignment/sync uses through shared helpers after UID
dispatch passes. Events, points, engine context and scheduling retain their
existing specialized modules; parity tests cover their envelope/type boundaries.

## Why tests alone are insufficient

A fast, table-driven contract test is the first step and remains necessary.
Run each datagram through real adapters with fake effects and compare tags,
destinations, receipt JSON, state transitions and operation calls. Test one
canonical expected outcome from the ratified contract as well as cross-adapter
equality; the common `enabled 0.5` bug proves why.

Test absent/extra arguments, wrong UID/selector, int versus float versus string,
out-of-range/non-finite numbers, malformed/truncated datagrams, and unknown
verbs. Cover persistent/ephemeral hosts, Performance transition/refusal, failed
persistence/effects, invalid manifests and listings. Drive deferred callbacks
and fake time for IO queues, receipt timeout and leases; retain current deeper
`test_io_control`, `test_io_reinit`, `test_io_stream` and Performance tests.
Every verb-table entry requires positive/negative fixtures and adapter bindings.

Tests alone would catch sampled drift but leave three places to update and
leave unsampled drift possible. A full shared node daemon is unnecessary.
The small shared boundary prevents repeated schema/grammar decisions; tests
catch adapter mistakes and shared mistakes. Neither makes physical effects or
all semantics mathematically impossible to diverge.

## OSC libraries and the Pi image

The node installer creates a venv from the image's `python3` and installs
`python/requirements.txt`: **pyOSC3 1.2**, pinned by root constraints. It does
not install python-osc on a node. The laptop IO requirements inherit that file.
Dashboard/dev installs both libraries: pyOSC3 1.2 and python-osc 1.10.2 on
Python 3.10+, **python-osc 1.8.3 on Python 3.9**. Installed host metadata says
1.10.2 requires Python >=3.10; pyOSC3's metadata has no `Requires-Python` field.
No conclusion about supported Python versions follows from that missing field.

These are provisioning declarations, not verified image contents. INSTALL calls
for Raspberry Pi OS Lite 64-bit, records a historical Trixie/Python 3.13.5 build,
and explicitly says current rig OS/Python/package versions are unchecked.
A read-only attempt to query `bop000.local` failed name resolution, including
outside the sandbox. No installed Pi version was observed; no device was updated.

The split is wider than the three files: pyOSC3 also owns bridge servers and
bundles in `python/io/main.py`, IO receipts/stream decoding, and fake stream
bundles in simfleet. Dashboard IO consumers decode those bundles with pyOSC3.
There are 11 Python files under python/dashboard/tools importing either OSC
library. Library replacement would therefore touch IO and its byte-preservation
guarantee, not merely an import in `bopos.py`.

In the installed host venv (Python 3.14.7, pyOSC3 1.2, python-osc 1.10.2), five
cross-codec samples (`i` int32 max, `f` .25, long timestamp `s`, UTF-8 `s`, binary
`b`) emit identical bytes and decode correctly in both directions. This is no
proof about every tag, malformed packet, bundle/timetag, or Python 3.9 behavior.
It does show that observed administrative drift is above the sampled codec layer.
The double-token ping mismatch is type information lost by simfleet's inferred
reply construction; explicit tags in the common reply helper address that without
changing libraries.

**Decision:** keep the codecs in their adapters now. A shared pure protocol
module needs neither OSC dependency. If later consolidating, prefer an explicit
python-osc migration experiment, using the existing 1.8.3 floor branch rather
than raising Python's floor. First test exact stream bundle bytes/order/tags,
server/client error handling and reconnect, ping echo types, events/timestamps,
and import/execute under actual Python 3.9. The current source guard for postponed
annotations is useful but not a substitute for that interpreter run. Record a
current Pi's OS, framework revision and venv packages before any package change,
then perform real engine/IO verification. Do not use "pyOSC3 is old" as evidence
that replacement is required for this extraction.

## Horizon fit, alternatives and cost

The shared boundary is **device administration**, keyed by opaque UID; it owns
no singular Pd process, engine port or Seat-to-process assumption. Fact/operation
adapters select today's engine target. The future several-engine device can
replace that selection without copying wire grammar. New engine-instance
addressing and report shapes remain Bob's horizon decision; do not invent an
engine identifier, array of engines or broadcast fanout here. Existing selector
and engine-context primitives remain reusable for non-Pd engines.

Rejected alternatives:

- **Parity tests only:** worthwhile first gate, but retain duplicate decisions
  and manual synchronization indefinitely.
- **Subclass/import the real daemon:** brings global socket/state initialization,
  Pi observations and lifecycle coupling into tools; makes horizon changes harder.
- **Make audition inherit simfleet:** replaces duplication with fake-IO/delay
  coupling in an actual engine relay. Share wire rules, not the simulator model.
- **A generic protocol DSL/plugin/effect framework:** more machinery than the
  fixed verb surface needs. A flat table and functions are sufficient.
- **One OSC library first / rewrite all LAN dispatch at once:** adds IO/server
  migration risk without repairing the measured validation/schema faults first.
- **Shrink the contract to audition's subset:** removes working device features
  and creates another capability/version policy. No ratification supports that.

Budget estimate, not a measured patch: roughly 160–220 lines of shared pure code
and 30–70 lines of adapter binding, replacing about 240–360 repeated lines across
dispatch/receipt construction (roughly 50 more to 170 fewer runtime lines before
audition's missing behavior). Parity fixtures likely add 200–350 test lines.
Completing audition adds unavoidable operation/state code; measure that separately
from extraction. Do not claim the 1,250-line census as a deletion opportunity.
Keep each extraction net small or smaller; if adapter scaffolding outweighs the
removed decisions, stop at shared validators/builders and reassess the dispatcher.

Ordered implementation after ratification:

1. Land fast contract/parity fixtures and small defect repairs: malformed sync
   must not escape; malformed assignment must not mutate state; enabled 0.5
   must not be coerced into a valid switch. Use full manifest validation in
   simfleet and preserve ping token tags. Preserve existing valid wire forms
   and receipt shapes.
2. Extract shared grammar and report/receipt builders; replace callers one
   surface at a time. Use the real IO receipt builder's existing invalid-input
   convention consistently. Require all adapters to provide complete reports.
3. Connect the small common UID table/dispatcher and complete audition's missing
   existing-contract bindings. Preserve asynchronous reply ownership and
   execution-time Performance checks. Run fast tests and affected browser
   journeys (device IO, stream/reinit, Performance, Wi-Fi, log destination and
   audition output). Check operation failure and timeout cases before deleting
   old branches.
4. Measure the resulting LOC and remaining duplicated decisions. Run one current
   Pi's engine/IO gate separately from software parity. Library migration and
   engine-instance design remain separate proposals, not automatic next steps.

This stitch stops at the proposal gate. Runtime, dependencies, contract and
Pure Data files are unchanged; no commit or loom state command was made.

Verification: the probe executes successfully and records the disagreements
above. Evidence assertions checked census totals, source hashes, expected exception
and state differences, codec bytes and manifest rejection/acceptance. Its source
parses with Python 3.9 grammar; it ran on Python 3.14, not a 3.9 interpreter.
No production test suite, live engine, bus, audio or physical network gate was run
for this proposal-only task.

## Fixed ahead of the ruling (lead, 2026-10-04)

The malformed-sync defect was fixed immediately (fix-and-simplify-first: it could take a real node off the network). A `/sync/ping` with a non-integer sequence is now ignored, and `lan_listener_loop` guards each datagram, so no handler error can stop the listener. Tests: `tests/test_event_plane.py` `LanListenerRobustnessTests`. The other defects (malformed assignment, enabled 0.5, simfleet manifest validation and ping tags) wait for the ruling.
