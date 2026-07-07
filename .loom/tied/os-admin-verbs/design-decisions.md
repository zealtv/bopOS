# os-admin-verbs — decisions and proposals

## Decisions taken (within the ratified contract)

- **Reply timing.** Lifecycle verbs (`reboot`, `shutdown`, `restart-engine`)
  send `/os/rev` *before* executing — after is impossible (§7). Provisioning
  verbs reply *after* the delegated callback returns, so the sha in the
  receipt is the post-pull one: that's what makes "update all and watch them
  come back" observable rather than fire-and-forget.
- **Delegation.** The 6660 handlers call the existing 7770 callbacks
  positionally (`callback('', '', args, '')`) — one implementation, two
  spellings, and the deployed fleet keeps migrating on aliases (§13).
- **Threading.** Provisioning callbacks block for up to minutes (git pull,
  clone, download), so they run in a daemon worker thread serialized by
  `admin_lock` — the 6660 listener keeps answering ping/params during an
  update, and two provisioning verbs can't interleave in one git tree.
- **Ephemeral model.** Provisioning verbs are an honest no-op with the
  receipt still sent (§7). Lifecycle verbs execute regardless of model —
  rebooting an ephemeral node is meaningful and allowed.
- **Dashboard sends `/os/*` only** for admin verbs — no legacy double-send.
  Params are idempotent full-state so double-sending is safe; admin verbs are
  not (a doubled `update` runs two pulls, a doubled `reboot` reboots twice).
  Old dashboards keep working against updated nodes via the PD-routed 7770
  aliases; the new dashboard requires contract nodes.
- **Malformed args** (e.g. `/os/checkout` with no branch) change nothing and
  still get a receipt — the convergence assertion reports the honest state.

## Proposals for Bob (ratify or reject; nothing blocks on these)

### 1. `/os/rev <sha> <model> <uid>` — trailing uid (additive erratum)

The contract fixes the receipt as `/os/rev <sha> <model>` (§7). The reply is
unicast, so on a real fleet the source ip attributes it — but simfleet's
devices share one ip, making dashboard-side attribution impossible during the
mandated simulator verification (and fragile on any multi-homed/NAT setup).
Implemented: helper.py and simfleet append the uid as a third arg; the
dashboard prefers it and falls back to unique-source-ip. Extra trailing OSC
args are ignored by receivers that don't expect them, so this is wire-
compatible both ways. Same pattern as `/os/pong <token> <uid>` (§6).
**Ask:** bless the third arg into the contract text.

### 2. `/os/getsamples` — keep the alias, then retire it onto `/os/fetch`

`getsamples` is not in the ratified §7 list; it exists on the wire today.
Implemented here as a plain alias of the legacy behaviour (delegates to
`getsamples_callback` → `bash/getsamples.sh`, replies `/os/rev`).
**Proposal:** once the fleet runs the fetch-landing code, remap it to sugar
for `/os/fetch gdrive:<active patch's SAMPLEPACKSURL> samplepacks` (replying
`/os/fetched` like any fetch) and deprecate the gdown script; one downloader,
one landing convention. Until ratified, the alias stays.

### 3. Real-node receipt race on `update` (note, not a change)

`bash/update.sh` ends with `sleep 5; systemctl reboot`, so helper sends the
receipt just after reboot is issued, inside the systemd stop window. UDP
almost always escapes in that gap, but if real-rig testing shows lost
receipts, the fix is to drop the reboot from update.sh and let helper reboot
*after* replying. Loopback can't exercise this; flagged in verification.md.
