# Implementation decisions

- Persistence is `bopos.control.cards = {version:1, targets:[...]}`. The old
  ordered `bopos.control.columns` records and the older single-target key are
  read only for migration; column ids, disclosure state, duplicates, and order
  are discarded.
- Runtime picker ids remain ephemeral DOM identity only. Target membership is
  the persisted identity, so no minted id survives a reload.
- Invalid committed selectors are removed only after the first venue `state`.
  The `venueKnown` gate therefore still prevents an early device heartbeat
  from erasing restored cards.
- The empty set is valid. `+ card` creates one unpersisted draft, and every
  committed card—including the last—can close.
- Duplicate targets are disabled in other card pickers and rejected again by
  the host callback as a programmatic-input guard.
