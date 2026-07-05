# Round 2 notes — Bob, 2026-07-05 (written, verbatim)

one thing i note is in the dashboard design document - the Gain, Gain2, and Backing osc
targets are patch specific.   echo echo'd osc message back - it can either be moved into
helper.py or removed/surplaced with better discoverability/debug design.

there's a smell about the osc ports - both in quanitity, their designated numbers, and
general protocol design.

both points regarding the osc schema design.

some points may be best addressed ahead of time as they might steer the dash development
and/or design.

zil.co was a a transcript error.  my website is zeal to co.  the belief project was
called "Belief System". It was sequenced via Ableton which was itself challenging and
unreliable due to the instability of Max for Live and the complicated sequencing.  A
better sequencing approach is required - either a stand alone app, or as something built
into the dash.

A simple scripting language for designing scenes could be one approach here. Scenes
could then be triggered, mixed, or crossfaded,  features should include loops for
looping sequences, one shot lines, lfos, "note" generation ie random number generation,
and rhythm notation.  look at how bop notates parameters - you should be able to read
this from the bop pd help patches assuming bop is pulled in as a submodule.  i jotted
down some other notation ideas in the past: https://zeal.co/notebook/intermals/.

a way triggering scenes across time ala abletons trigger slots is a known and useful ui
pattern for this.
scripting is much easier for composers now ai agents exist.

a workflow where an artist can prompt into place a sketch, as well as the patterns to
control it across many instances would be very powerful.

sample management has also proved a painpoint.  a flexible way to mass update the audio
running on all the pis would be very helpful.  utilising the local network is likely the
least painful way to do this.

regarding running alternative engines ala super colider.  I think this is something
worth seriously considering given supercollider is more agent friendly than pure data.
the bop framework -> the instigator of bopOS, is designed as a UI comfort and
convenience layer over PD aiming at broadening artist friendly workflows.  those are
different workflows ( hand-patched, hand-coded, agent-coded, collaborative ). for kite
choir, efficiency and agential workflows will probably prefer supercollider. RNBO is
another consideration - but potentially more comlicated with their runner that run on a
pi that may compete with bopOS.  more of a future concern.

Another sequencing idea that i have had in the past - is to use video as a mask across a
2D space.  the luminance, for example, of a given coordinate, could be mapped to a
parameter on a bopOS patch.  meaning visual gradients and video textures could be mixed
to create sweeps and other effects across a given space.  an open question is as to
where this happens - is it part of the dashboard? or another application? or something
else?
