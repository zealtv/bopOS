# Engine `/id` type — proposal for Bob

**Pending Bob's ruling. No wire or contract change is shipped here.**

Contract 1.18 §4.2 spells the engine message `/id <n>` without an OSC tag.
§5 fixes the resolved Seat identity and the unassigned value `-1`, but does
not specify an engine-facing int/float tag. OSC-REFERENCE's `/id <n:i>` guide
entry suggests integer; it does not override the normative contract's
unspecified tag. Today `apply_assign` and `apply_unassign` send `,f`, whereas
`config_callback` and `deliver_engine_context` send `,i`. A non-PD engine
can observe that difference even when the numeric values agree.

Checked `pd/bopos~.pd`: the engine input goes through `oscparse` and
`list trim`, then `route id groups os audition`; the id outlet reaches the
`id $1` message and `s bopos-context`. That source path does not inspect the
original OSC tag or require a float-only branch. This is source inspection,
not a claim of a live Pd/hardware run. No Pd edit is needed for the proposal,
so there is no new owed edit to add to `64-pd-edits-owed`.

**Recommendation:** explicitly ratify `/id <n:int32>` for every engine
delivery, including assignment/unassignment, `/config` replies and ready
replay. Keep the resolved numeric identity, unassigned sentinel, address,
argument count and delivery timing unchanged. After approval, change the two
assignment send tags to `i` and make the contract/reference agree. This changes
what engines receive on those two paths and therefore needs Bob's approval;
it is not part of this behaviour-preserving cleanup. Version scheduling must
be coordinated with Bob's still-pending stitch 68 amendment.

Alternative: preserve and document the current mixed tags, requiring engines
to accept either numeric tag. That avoids a wire transition but retains an
unnecessary distinction between initial assignment and later replay. The
current mixed tags are retained and covered by a packet-level regression until
Bob rules.
