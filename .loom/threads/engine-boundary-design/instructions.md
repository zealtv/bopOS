# engine-boundary-design

Define and ratify the engine-neutral boundary between bopOS core processes and
patch runtimes before extending the SuperCollider starter or audition rig.

The design must cover PD, SuperCollider, openFrameworks, and plausible future
engines without erasing useful process/port separation. It must settle:

- command ingress and whether engines ever forward administration to helper;
- the patch-facing provided-term, cue, point, notification, IO, and report APIs;
- ownership and delivery of identity, assignment, and run context;
- local bus/OSC naming, including the `bopos-` namespace;
- meter meaning, scope, subscription, rate, and fleet bandwidth;
- IO/peripheral port separation and high-rate streaming;
- diagnostic/echo behavior and removal of legacy cruft;
- production versus audition socket topology; and
- migration from today's working PD/helper/SC seams.

Authority: Bob ratifies the result. No implementation or contract amendment
lands from this thread before the ratification child is tied.
