# IO errors — proposal for Bob, not implemented

The v1.18 contract (§11 and the no-bus clause) specifies only
`/io/error <name> no-bus`. The existing bridge also sends
`/io/error <name> create-failed` when peripheral creation fails; this commit
preserves that shipped behavior but does not extend that undocumented token to
new failure cases. The contract and Pd files remain unchanged.

Software now catches malformed create addresses, poll rates and scan bus numbers
and logs them without changing state or killing the handler. Unknown verbs,
missing commands, extra peripheral path segments and raised writes retain clear
log diagnostics. Their requested OSC replies remain open because the ratified
contract supplies neither a suitable reason nor a name for bridge-wide failures.

## Options

1. Keep diagnostics in io.log until the broader `59/0a` IO design review decides
   their operator-facing destination and grammar.
2. Ratify a small error vocabulary using the existing two-value shape now.
   Recommendation: explicitly document existing `create-failed`, add
   `invalid-arguments`, `unknown-command`, and `write-failed`; define how
   bridge-wide errors supply `<name>` without inventing an unnamed reply.

Under option 2, proposed mappings (all pending):

| Case | Proposed name | Proposed reason |
| --- | --- | --- |
| Named create with malformed/missing type or address | requested name | invalid-arguments |
| Create setup/import/type failure | requested name | create-failed (already emitted) |
| Poll/scan malformed argument | poll/scan | invalid-arguments |
| Unknown `/io/<verb>` | verb | unknown-command |
| `/io/<name>` with no command or extra path segment | name | invalid-arguments |
| Peripheral write raises | name | write-failed |
| Bare `/io` or create without a name | unresolved; Bob must choose a reserved bridge name or other rule | invalid-arguments |

Using poll/scan as error names and adding a reserved bridge name are semantic
wire decisions, even though the shape stays `/io/error <name> <reason>`.
No such decisions or new tokens ship in this commit. Do not use `no-bus` for
argument/dispatch errors: that would give a false diagnosis.
