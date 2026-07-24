# Braindump — first full patching session (editor → simulator → device), 2026-07-24

Verbatim from Bob, after the most in-depth patching session so far: taking a
patch from the editor, to the simulator, to a device.

---

So, I just had a patching session using Bop! OS and things are working quite
well in a lot of ways, and this also surfaced that would be really nice to have.

One thing I've noticed is that in sequencing or generally controlling
parameters that are floats, it's really useful to be able to input a very
precise number. So the slide is great, but we also need to do precision float
input wherever we're controlling a parameter.

On the dashboard, what I find is when I'm running a simulation or really want
to zoom in on a single device and control it specifically.
Currently that means going to the seats tab and then finding the device, but I
noticed that as I start to put more interface elements or parameters on a
device, it doesn't fit within the window of the seats tab vertically.  It seems
like all of the Chrome is taking up much too much space, so the queues, that
whole queue section is much too big. Maybe that needs to be off to the side.
The amount of space for the device parameters is really short, and that
actually looks like it should be the focus, right? So on this interface, you
should be able to quickly choose what you're targeting or viewing, be it a seat
or a group or everything at once, and be able to see all of those parameters
very clearly laid out. This view where you see each individual seat in a grid
perhaps isn't the best approach.

It seems like that control surface is something that should be a pattern that's
reused throughout the application on different tabs.
So for example, when you're editing the patch you see the patch's control
surface and as you move those or interact with those parameters you can see
that updating in the patch as you edit it.

That same control panel gets presented in the devices panel or in the devices
tab exposing that device's parameters. So you can jump over to a specific
device and interact with it specifically regardless of what seat it's in

What's currently the dashboard tab and should be changed to the control tab
gives the same view but gives a filter for selecting that view, for example,
groups all specific seats, as well as exposing the cues, the master control,
and presets.

It seems like the presets primitive should be associated with a patch and its
manifest. So, a preset applies to a single device or a single seat.   We can
then have collections of presets that get applied to groups and seats, etc.,
but that same primitive is defined by the manifest.  The thing, the place that
I could see that being really useful would be, for example, if you're on the
patch edit page, and you're editing your patch while viewing that patch's
control panel, there would be a save preset in that control panel so I could
save a particular state of the patch. And then when I come over to, for
example, the control tab, formerly the dashboard, I could find a particular
seat and load that preset.

That preset could then also be applied to groups or all devices simultaneously.
I think we need to look at those approaches and find the best architectural
solution for what a preset should be.
