# Raw session notes — 2026-07-11

The following sections preserve Bob's messages verbatim.

## Helper forwarding, notifications, launch context, and identity

I've added the restart engine message to the process helper messages sub-patch. The sends associated with those messages previously were going to a feedback sub-patch, which was sending out audible tones to give some audible feedback when those messages were triggered. I've changed those sends to now be propended by notify - to make it clearer that these are notification messages. And I think I'll move the feedback patch into bopos.out~. I'll likely refactor this because I think there's probably a tidier way to do this by sending symbols through a single notification send and receive pair.

I've added an S notify identify to the route object connected to the net receive on port 6661.

And I'm also seeing things in this patch that I suspect we may either be able to remove or refactor, specifically the messages that I'm currently receiving from start.sh. That is a random seed, a start date, a start time, and the name of the active patch. These seem like things that should be the domain of BopOS and we should be sending these to pure data via helper.py not from the start shell script if at all possible.

There's also some ID routing machinery here that doesn't feel like it should be the domain of pure data. It feels like that should be a BOPOS responsibility. And that the patch would be receiving messages that are targeted to it but I think that's something that I need to have a conversation with you about.

## Deliberate deferral

Okay let's park the ID Machinery, the random seed, the start date, all of that, and let's stay focused on the Bop OS OSC PD edits. Those other items are something that I'm going to want to talk to a more powerful model about. So at the end of these pure data edits let's make a note that I'll be up to hand off to a larger model to start a design conversation with.

## PD-to-helper boundary smell

good catch. that's fixed. i should note there is a smell here - needing to forward from pd back to helper seems potentially unessecary and messy.  something to flag to consider in the upcoming design discussion.

## Meter semantics and traffic

bopos.points fixed.

It strikes me that having level metres constantly on in a BOPOS.OUT object Is likely to jam up the network, especially if we have lots of devices with lots of elements. If metres are to be volume metres associated with the output of a specific element then we're going to need one metre per element. And we're going to need a way to turn them off. But alternatively maybe we consider metres to be a kind of feedback for the dashboard that can be created synthetically so that we can get more control from the patch and use them more flexibly. I think this needs some consideration.

## IO ports, naming, cruft, and cross-engine abstraction

continuing brain dump from previous recent messages:
noticing a slight smell in the i2c peripheral handling.  receiving osc message -> forwarding directly to io/main.py.  making things simple for different engines is what is cueing me to this, as the SC starter will also be binding to multiple ports, sending traffic in various directions.  But also - splitting traffic across ports has significant performance benefits - especially as i2c devices can be streaming a lot of data.  my current strategy is one of clearly labelling sends and receives [s to-bopos-io] and [r from-bopos-io].  this is feeling right at the moment. messages are still forwarded to  8880 from 6660 if they match /io. this is definitely required for later controlling lights, actuators etc. documentation and clarity is key here.  clarity should come out of clean design.

But similarly, if this can be abstracted cleanly within bopos.osc.pd (which should probably just be called [bopos.pd]), the patching experience can remain understandable.

The [r osc-in] and [s osc-in] also feel a little vague as labels.  [r from-bopos] [s to-bopos] is tempting, even if it is inaccurate. perhaps some appropriate verbeage can be found.

[sidenote - helper.py feels like it should be renamed to bopos.py]

I also see there is potentially a lot of cruft in the bopos.osc patch: the echo functionality that forwards incoming messages back out over 5550.  How does this fit with the current bopos spec and design? it's something we've found useful (for example printing out sensor values from an i2c peripheral) to help debug.  Other cruft: [r PX]->[print PX] etc.

[r osc-in]->[route id]->[s ID] is a prickly one as that is for dynamically setting the id, though that certainly feels like a bopos responsibility.

Since similar abstraction will be created for SC/OF/ whatever, the exact role and function of that abstraction is something that should be isolated, clarified, and articulated.
