# param-address-0-design

Design the additive OSC/manifest change for custom nested patch parameter
addresses. Bob's motivating examples include:

- `/instrument/marimba/gain`, `/instrument/marimba/bright`;
- `/instrument/glok/gain`, `/instrument/glok/decay`;
- `/fx/echo/repeat`, `/fx/echo/mix`;
- `/fx/reverb/decay`, `/fx/reverb/mix`.

Resolve whether the manifest stores a path separately from its display name or
allows slash-separated names; define the canonical `/p/...` fleet and engine
address, validation/escaping rules, grouping/tree rendering, stored-value keys,
catch-up, `/all` behaviour, editor CRUD and compatibility/migration for current
flat names. Survey OSC library/Pure Data address handling, but never edit `.pd`.

Deliver a short contract/design proposal, lore-keep it, and return to waiting
for Bob's ratification. Parked from the 2026-07-15 tabs-0 session until Bob
explicitly resumes it after the current UI-tabs runway.
