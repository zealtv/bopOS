# 5-hierarchy-and-persistence

Third slice of the ratified control-panel design (authority: the tied
`2-control-panel-design` stitch).

Accordion chrome for nested parameter addresses per design-language §9:
`▸ name` / `▾ name` disclosure rows, children indented 12px, replacing the
current always-open `.live-param-branch` sections. Collapsed state persists
per address (localStorage, keyed by scope + branch path) so an operator's
pruning survives re-renders and reloads. Note the Control surface is an
iframe — localStorage is the shared state channel (CLAUDE.md gotcha 15).

Verify: living journey covering collapse → heartbeat re-render → reload.
