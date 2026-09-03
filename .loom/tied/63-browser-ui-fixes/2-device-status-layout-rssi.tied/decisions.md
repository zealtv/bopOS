# Decisions

## Device-card order

The existing Actions section moves intact to immediately follow the first
device status section. Its markup, button set, enablement, confirmation path,
and exact-UID send bindings are unchanged.

## RSSI meaning

The status card classifies reported Wi-Fi RSSI as:

- good: `>= -60 dBm`
- marginal: `-61` through `-75 dBm`
- poor: `< -75 dBm`
- neutral: missing, non-numeric, or wired/unavailable

The visible value remains present and gains the words `good`, `marginal`, or
`poor`, so color is supplementary. A small filled status dot and the matching
semantic token provide the restrained visual cue; neutral uses the existing
dim ink and a hollow dot. The same token-based rule operates in both themes.
