# Control-panel UI mockup — Bob's annotation text (verbatim transcription)

Transcribed from the annotation panel of the mockup image Bob attached in chat
on 2026-07-27. The original image stays with Bob; four mockup panels are
described after the transcription.

---

So the interface is tight and compact, drawing inspiration from Pure Data,
Ableton, MaxMSP, primarily grayscale, monochrome-ish, with some highlights,
cyan highlights, the cyan color indicates either selection, but predominantly
modulation. Clicking the modulation icon to the right of a parameter expands
the modulation control panel where you can choose the kind of generator, you
can then control or set up its parameters. Clicking the modulation indicator
again collapses that generator control panel. But the parameter remains under
control of a generator until you click the slider or enter a value or interact
with that UI manually in some other way.

Parameters under hierarchical addresses are able to be accordioned up or down
to be hidden. So for example in this there is a reverb which is currently
collapsed and if you expand that it might have additional addresses underneath
it that in turn could be expanded.

There's a delay address there that has been expanded, and the time parameter
is an example of mixed generators, or generators and values. The wet parameter
under delay is an example of mixed values. So the dashes or crosshatching
indicates mixed, and if it's blue or cyan, it indicates there's a generator
involved. And in these instances again, editing that parameter would then set
all of the targeted seats parameters to whatever you set them to, and they'd
no longer be dashed or cross hatched, they'd be solid, indicating a unified
value across the targeted seats.

I've put a preliminary preset UI at the top of the control panel. This is sort
of provisional thinking at the moment ahead of the preset system.

I have here really only float values, But we need to also consider toggles,
integers, as well as events which I haven't specced out yet, but events will
either be individual floats, pairs of floats, primarily used as MIDI note and
velocity pairs, and triplets of floats which will be usually MIDI note
velocity and duration.

We're going to want to be able to extrapolate from this design some of the
design language rules. For example, a parameter exists on a single line. We
try to make those parameters not too tall. You can click to enter numbers
precisely and modulation wherever possible displays its current value and its
current visual modulation in the case of like a slider being blue and sliding
up and down But also, this should be in the case of, for instance, instance
toggles. They should visibly flash on and off as a visual indicator of their
value - and have blue/cyan border indicating they are running a generator. And
that also goes, if at all possible, for sample and hold and drift, although I
understand but they might not be as deterministic, but if they are
deterministic, we want a visual representation showing the precise value as
well as that visual indication of the slider or the toggle or whatever it is
showing its current value if it's under the influence of a generator.

We may at a later time also want enumerators which will just send over the
wire as an integer, I imagine, and we'd need to consider what, if any,
automation is applicable in that case if they are able to be automated in the
same way as integers.

The event type of the single double or triple arrays of integers or floats in
the case of usually MIDI notes Will need to be specced out carefully - we are
likely going to want to be able to implement forward synchronization with
those kinds of events - so these are probably a new plane ie `<target>/e/*`

---

# The four mockup panels (described)

**Panel 1 — "All Seats" control panel.** Header "All Seats" with a "send all"
button. Patch name `bonks-pd` with a provisional preset row: `preset 1`
dropdown + `new` / `save` / `del` buttons. Parameter rows, one line each:
numeric value box (e.g. `0.8234`) + named slider (`gain`, `filter`) + a `~`
modulation icon in a circle at right (cyan-highlighted when a generator is
active). Below `filter`, an expanded generator drawer: LFO / loop / fade tab
buttons (LFO selected, cyan), a waveform display (triangle, `tri` dropdown),
`phase` and `curve` mini-sliders, and `min` / `max` / `period` value boxes
with a seconds-unit dropdown and a cyan `free` toggle. Then a `cutoff` row,
a collapsed `▶ reverb` hierarchical address, and an expanded `▼ delay` with
`time` (cross-hatched slider + cyan `~` = mixed with generator involved) and
`wet` (cross-hatched, plain `~` = mixed values).

**Panel 2 — fade generator drawer.** Same tab row with `fade` selected
(cyan). A curve display, `from` value box (`0.0`), `curve` mini-slider, and
segment rows: `to <value> in <n> <s▾> remove`, plus an `add segment` button.
Multi-segment fades are composable.

**Panel 3 — non-float controls (right panel).** `enable-fx` toggle shown in
two states: "toggle (generator)" (cyan border = generator-driven, flashing
with value) and "toggle (value)" (solid cyan = on). Event rows: `64.0
event[1]`, `64.0 127.0 event[2]`, `64.0 127.0 2000.0 event[3]` — single /
pair / triplet float arrays (MIDI note, velocity, duration) each with `sync`
and `send` buttons (forward synchronization). An `127 integer` row with `~`
icon, and a `mode-1 ▾ enum` dropdown row with `~` icon.

# Design-language rules to extrapolate

- One parameter per line; rows kept short/not tall.
- Grayscale/monochrome base; cyan = selection and (predominantly) modulation.
- Click-to-type precise numeric entry everywhere.
- Generator state is always visible on the control itself: slider fill
  slides with the modulated value; toggles flash their live value with a
  cyan border; deterministic generators (incl. sample+hold/drift if
  deterministic) show the precise current value too.
- Manual interaction with a generator-driven control takes over (consistent
  with the ratified §3.2 hard-takeover semantics).
- Mixed aggregate state: cross-hatch = mixed values; cyan tint on the
  hatch = a generator is involved somewhere in the aggregate; editing
  unifies and solidifies.
- Hierarchical addresses accordion; collapsed by default state per address.
- Events are likely a new plane, `<target>/e/*`, needing careful spec
  (contract amendment) including forward synchronization.
