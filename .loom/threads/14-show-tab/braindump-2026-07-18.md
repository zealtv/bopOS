# Bob's braindump — sequencer tab first slice (2026-07-18, verbatim)

brain dump for sequencer tab first slice (it's a meaty slice):

Sequencer tab gets named something else

It is a 1 column, many row table (more columns later to be more Ableton like possibly)

Rows may be empty

Rows have sets of osc messages that gets triggered together.

Rows and osc messages have aliases

Osc messages shown as blocks/pills

Rows and messages can be focused and present their properties in a context sensitive inspector.

A group of rows delimited by empty rows i am refering to as a collection.  please come up with better terms where available (see below)

Rows have a trigger/play button that displays their current state, allows for starting, stopping, pausing, triggering their next action. (if any of these make more sense in a global transport control, you can add that).

Rows have:
- duration
- play n times
- then:
- - stop
- - play again
- - next row
- - previous row
- - any row in collection
- - other  row in collection
- - go to (target a row by alias another uid)
- - next collection
- - previous collection

Any plays a random row from the collection of rows delimited by empty rows.  Other does the same, but keeps track of which rows from that collection have been played already (Ableton behaviour).

More than one "then" action can be added.  The next action then chooses randomly from them.

If we have provisions for forward synchronising any osc message, that should be something that can be set in the row inspector.

Duration can be set in hours minutes seconds for now - we will want a global transport with the option musical time later.

The osc messages inspector should help construct osc messages - choosing targets, picking parameters, points, or cues, this is where the decomposed curves will live.  As well as the specifications for motion of points.

You should be able to copy, cut, paste, move, and delete osc messages between rows.

There should be two consoles - one for outgoing osc messages, one for incoming osc messages.  You should be able to filter these consoles by string including Asterix wildcards and exclamation negation.

At some point - once point motion is better dealt with, as well as gradients etc, a visualisation of these animated properties (a similar view to the seats view) will be very helpful.

This tab is the primary performance control tab.  Feel free to choose better terms for rows, collections of rows, the name of the tab etc.
