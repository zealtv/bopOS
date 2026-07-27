# Braindump — events/cues, global controls, manifest reordering (2026-07-27)

Bob's message, verbatim (spoken-dictation spellings preserved; "queues" =
cues):

> get this into the loom for me. it might subsume or inform other stitches. A
> note regarding the events design - I noticed something that would be really
> useful to be able to do is trigger queues for groups or individual seats or
> all seats, that is, I think queues should actually be on the control panel,
> not separate. The lead time remains a global control that gets positioned
> with the master fader, but it also strikes me that master, lead time, and
> mute are kind of now global controls that we should find a new home for,
> either persistent in the top menu bar or in their own panel down in the
> monitor.
>
> cues become a kind of event. So a cue is an event with zero elements. Events
> can also have one, two, or three elements for plain MIDI notes, median
> velocity, MIDI velocity and duration, but really these could be anything
> that just floats.
>
> I also noticed that in the patch tab where you specify the manifest, it
> would be really useful to be able to drag the parameters and events around
> to reposition them so we can reorder the control panel.
>
> With cues becoming zero element events, maybe this is a deeper design
> decision than simply creating a new event plane. Maybe cues get absorbed
> into the event plane. Then the control panel will have a section for
> parameters and a section for events. That's probably easier at this stage
> than being able to intermingle events amongst parameters And also means we
> can leave the patch manifest construction area less changed.
>
> As far as a home for the master, mute and lead time controls, let's try
> putting them in the monitor panel to start with. And it also means maybe we
> should reconsider the terminology regarding the monitor panel down the
> line. Monitor is fine for the moment, but just a note that we might want to
> revisit that Since we'll likely end up with a seat map and maybe some other
> visualizations down there, so something to dwell on.

("median velocity" is almost certainly dictation noise for "MIDI note +
velocity" — the arity ladder is note / note+velocity / note+velocity+duration.)
