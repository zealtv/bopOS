# device-alias-vocabulary-expansion

Double the curated device-alias vocabulary from 64 to 128 global given names
and from 64 to 128 character-word surnames. Keep every token short, ASCII-only,
easy to pronounce in English, and unique within its list.

Preserve already-persisted aliases exactly. Treat the expanded allocation as
generator v2 and retain an explicit v1 compatibility path so the original
pinned candidate vectors remain reproducible. New allocations and Reset use
v2; loading an existing v1 registry entry must not rename or upgrade it.

Add a focused browser-free verifier covering list size/quality, legacy v1
vectors, stable v2 vectors, collision probing across the larger space, and
restart preservation of an existing generated alias.
