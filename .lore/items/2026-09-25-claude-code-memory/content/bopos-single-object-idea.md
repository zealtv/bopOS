---
name: bopos-single-object-idea
description: Bob wants to merge the required PD abstractions into one object; composer workflow needs a real walkthrough first
metadata: 
  node_type: memory
  type: project
  originSessionId: 53d62878-b0d5-47ab-9267-f6caafb011ff
---

Bob's hypothesis (2026-07-13): the required patch-side PD abstractions
(`[bopos]` + `[bopos.out~]`; `bopos.audition~` is already private inside
`out~`) can merge into a single composer-facing object. Assessment given:
plausible — clone semantics favour it (singleton by construction), needs a
one-line contract §4.2 amendment (Bob ratifies), and should wait until
`preview-0-channel-model-spike` ties since that agent works inside
`bopos.out~`.

**Why:** the composer workflow is the real driver — Bob says it needs a
real-world stepping-through (him + agent walking the bring-a-patch flow on
the Zero), which is `friction-0-docs`'s first item and would empirically spec
the merged object and feed `friction-1-starter-kit`.

**How to apply:** don't design the merge on paper; propose the live
walkthrough with Bob when patch-workflow comes up. PD edits are Bob's.

Related: [[bop000-dev-pi-access]].
