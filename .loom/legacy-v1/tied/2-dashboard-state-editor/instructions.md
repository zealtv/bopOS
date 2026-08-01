# 2-dashboard-state-editor

After `1-contract-model-relay` is tied, implement the second ratified seam from
`.loom/tied/param-address-0-design/proposal.md`:

- use canonical slash-joined qualified identities for dashboard state,
  defaults, catch-up, same-patch schema revision, safe pruning, and presets;
- add manifest-editor path CRUD as slash-separated author input serialized to
  an array, preserving `name` as the leaf and keeping legacy `group`
  presentation-only and mutually exclusive with `path`;
- treat path/name changes as remove plus add, retain values for unchanged
  qualified identities, and send only active declarations when loading presets;
- render and bind nested editor/tree data without losing qualified identity.

Retain focused backend and Playwright verification plus exact results in this
stitch. Cover flat/nested keys, duplicate leaf names in separate branches,
edit/send, individual and `/all`, reconnect/catch-up, preset save/load,
same-patch revision, rename/move warnings, pruning, and flat compatibility.

Do not build the promoted Dashboard/facilitator live-control surface. That
flat/nested x All/Group/Seat integration belongs exclusively to
`12-dashboard-live-controls`. Never edit `.pd` files.
