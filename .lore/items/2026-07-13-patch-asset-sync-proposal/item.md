# Unified patch + asset distribution proposal (dist-0)

Design proposal awaiting Bob's ratification: the bopOS host's `patches/` and
`assets/` directories mirror onto devices via the existing §9 fetch
convergence machinery (`patch:` slot prefix), git stays available but never
required, `templates/` dissolves into demo patches, patch-level
`bopos.config` and the getsamples UI retire, and the dashboard gains
Send/Sync, a patch dropdown, and honest button names. Ends with six open
questions (Q1–Q6) that are Bob's to answer.

## Source

Written for `patch-asset-sync/dist-0-proposal` in response to Bob's
2026-07-13 composer-experience brain dump. The two survey files are
code-fact inventories (file:line) gathered by subagents the same day; the
proposal's claims about current behaviour rest on them.

## Related

- `.lore/items/2026-07-13-composer-experience-brain-dump`
- `docs/OSC-CONTRACT.md` §7, §8, §9
- `.loom/tied/fetch-landing`, `.loom/tied/patch-manifest`,
  `.loom/tied/patch-and-install-mgmt`

## Tags

- proposal
- decision-record
- patch-distribution
- assets
- osc-contract
- dashboard
- composer-experience
