# UI unification braindump — Bob, 2026-07-30 (transcribed)

Recorded from the opening message of the 2026-07-30 session. Lightly
punctuated from speech; wording preserved.

---

So I'm ready to start to look at unifying the user interface, in particular
adopting some of the conventions that we extrapolated out of the Excalidraw
mockup when we built the control panel. I'd really like the UI to be reusing
consistent components wherever it can. In the first instance, that is the
control panel. So anywhere there is a control for a patch, that should present
the same control panel with the same UI and the same features.

But I can also see, for example, on the step page we have a target selector
which lets us select all or groups or individual seats, and this feels like
it's a potentially useful reusable component that we could use in other places,
like in the Control tab.

Currently in the Control tab we have these radio buttons at the top — all,
groups and seat — and then a single control panel. But the control panel works
really well when it's a relatively narrow column. So rather than having just
one control panel, I think what would be really useful would be the ability to
create columns, with each column being a control panel, and placing a target
selector UI that can pop out at the top of that, so you can create different
control panels that are targeting different devices. And those devices can be
targeted either as all, or a selection of groups, or a selection of seats, or a
mixture of all of them, using that consistent target UI device. And then having
some simple ability to add and remove these columns as required, with a minimum
of one, so there's always one control panel when you get to the control panel.

There's also a lot of wasted real estate. So for example the "open standalone
dashboard" button — I think that can be another tab up in the tab navigation
where we have Show, Control, Seats, Devices, Patches and Assets. I think
right-aligned we could have — I'd like you to find a better name for it, but
it's like the tablet facilitator view — something that's a nice short title
that can be right-aligned in the tab bar, just so we've got a link. And that
means we could get rid of the text that says "Live control" and "Control". That
text isn't doing anything. We don't need it at all.

And that's a pattern that can be applied across tabs. So there's also
"single-device delivery" and "Assets" at the top of the Assets tab — that's not
required.

In the Patches tab, it's looking better now that we have movable parameters in
the manifest, but there's still some awkward layout. So in the fleet patch
deployment, we have the patch above the target. Here it would make a lot more
sense for those to be side by side, so that the patch, the target and the
buttons are all in a single line. This is one spot where I don't think the
target picker is necessarily the right user interface object — but if it is, or
if a variation of it is, then this would be a good spot for that as well. But
here we're targeting devices rather than seats. So perhaps a device picker and
a seat picker are two different things.

Stylistically, I think we've come across a nice set of user interface objects
with the sliders, number boxes and buttons et cetera in the control panel, and
that's the kind of styling that I would like to be able to roll out across the
app.

The control panel however does reflow a little awkwardly. Parameters need to
stay as single lines, so a number box, a slider and its modulation icon should
all stay on the same line as the parent becomes narrower. The modulation pop-out
shouldn't reflow either, so that should be just a set interface — perhaps that
can be used to set the minimum width of the interface. As long as that's
reasonable on a phone, I think that'll be fine.

I think the key here is that this is a desktop application, and so we want to
use a desktop application design language, like a professional piece of
software. So icons where there are buttons in toolbars, these sorts of things.
Basically what we want to get away from are these big, high-padding, bloated
buttons which are well intentioned — as they're designed well for touchscreens
or phones — but again, this is a desktop piece of software. And so if we need
to style it completely differently on the mobile side, that's fine, but on the
desktop side we want a nice compact, minimal environment.

I think a good process here might be to do a pass to identify the reusable
components, and then design them one at a time, and then integrate them into
the application, and then out of those components extract a coherent design
language where we can reuse number boxes, sliders, all of that styling. We want
a really tight, consistent style that we can apply to the application broadly,
that can be derived out of those initial reusable components. The control panel
is obviously the first of these, and perhaps the target UI might be the second,
but I'm sure there are other reusable components that we can extract out of the
application and give some attention to.

Another thing that I'm noticing is that in the inspector on the Show tab, that
should be using the control panel — right? — or the LFO modulation panel where
that's appropriate. And I think it's also useful to notice that the inspector
is like a narrow column, so that's well suited to the UI elements that we've
created for the control panel. But it also means that we can fit the generator
inspector that we have in the Control tab into the inspector on the Show tab,
because of that narrow width and consistency.

The Excalidraw I think should be the guiding north star — the closer we can
match it the better.
