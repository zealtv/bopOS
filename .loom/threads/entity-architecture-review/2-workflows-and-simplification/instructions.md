# 2-workflows-and-simplification

After `1-system-map` is tied. Walk concrete workflows over the as-is map,
surface the consequences, and propose the simplest model — then take it to
Bob for a review session (mark `.waiting` when the written proposal is
ready).

Workflows to walk at minimum (from Bob's 2026-07-27 braindump):

1. A show step loads a new patch (fleet-wide) mid-show, then sequences its
   params and applies its presets.
2. Different patches on different devices during one show.
3. Re-siting an installation: seats repositioned vs re-targeted; what in a
   show file has to change, what shouldn't have to.
4. Authoring: save a preset while sculpting in the patch editor; later use
   it from the Control tab and trigger it from a show.
5. A patch/manifest edit after shows and presets reference it (drift).

For each: which entities are touched, which references can dangle or loop,
and what the operator has to keep in their head.

Then the proposal: the recommended entity model and dependency direction
(what references what, by what key), a manifest-drift/fingerprint policy
sketch shared by shows and presets, and a short ordered list of **small,
working-system-preserving changes** that move toward it. Explicitly check
the proposal against `41-preset-primitive/1`'s already-ruled points
(patch-folder presets, shows composition-level with fingerprint references,
hard takeover, individual targetability) — extend them, don't contradict
them; where the review genuinely argues a ruling should change, flag it as
a question for Bob rather than assuming.

Success criterion, Bob's words: simplicity that allows flexibility and is
simple enough to keep the system in one's mind. The tie of this stitch
un-gates `41-preset-primitive/1-preset-architecture-design`.
