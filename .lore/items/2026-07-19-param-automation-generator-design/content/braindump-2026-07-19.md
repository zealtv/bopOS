# Parameter automation braindump — Bob, 2026-07-19 (verbatim)

i want to expand the way parameters are handled here is a brain dump.  help me
clarify this. i want timed fades to be able to be sent as single messages and
decomposed device-side.

what i want to acheive is effectively
/this/parameter from 0.0 to 1.0 in 10 seconds

time units:
seconds
minutes
hours
bars
beats
... others?

and someway to control the curve
linear
ease-in
ease-out
ease-in-out

ints should also be able to have the same timing format but should increment
across the

bop uses this shorthand:

1 element - go to x:
/param x

2 element - go to x in y ms
/param x y

3 element - go from x to y in z ms
/param x y z

4+ elements with equal number of items - destination duration pairs

4 elements - go to a in b ms, then c in d ms
/param a b c d

6 elements - go to a in b ms, then c in d ms, then e in f ms

/param a b c d e f

odd lengthed lists >= 5 error

lists of 3 elements can be looped wit the key word loop

/param loop x y z

loops are ignored for one and two element lists

stop freezes output:

/param stop

Things that work:  compact and flexible wire format.  Things that might not...
ms not always the right unit.  a string is likely better

1ms
1s
1m
1h
1b 1 beat
b1 1 bar
3b 3 beats
b8 8 bars

no argument is linear
1e full ease-in
0.5e half ease-in
e1 full ease-out
0.1e1 slight ease-in, full ease out

aside from floats and ints i also want to able set parameters to be:
strings
mixed arrays

in which case the manifest is setting the key to interpreting the messages
along the wire as these are predetermined.

---

the next step which i hadn't yet implemented in bop was LFOs

can you suggest a syntax for lfos?

---

I want these features to then become implemented in the show panel with a gui
for constructing automated parameters without needing to memorise the syntax.

---

and beyond this still - i would love the interface objects in the bopOS dash
to move, visualising the automated parameters.  Touching the automated slider
would send a simple paramter command /parameter 0.5 setting the parameter to
be static.

---

what do you think about this?  where would you push back?  where might you
extend or simplify?

## Second pass — Bob's rulings on the agent pushbacks (same session)

1. curve exponent is good, let's go with that.
2. yes - let's let the authoring layer handle it [musical units] - perfect
3. what if strings and arrays are something other than a "parameter"? then we
   can also defer implementation and everything stays readable.
4. i like your solution [clock-anchored LFO phase + catch-up sends computed
   current value for fades]
5. yes - decomposing in bopos.py is the right place.
6. loop would snap back - makes most sense since it is literally looping the
   curve as described.  stays consistent with longer multi-segment lines.
   triangle lfo handles the ping pong case.

the lfo syntax shape is great. love the shapes.

one thing on the gui side - when visualising lfos or automated params, some
sort of waveform visualisation would be extremely helpful.  it might also be a
good way to indicate a parameter is automated. it quickly fades out when the
slider is touched since the parameter is returning to a static value.  i'd
want a ui/ux designer eye over that to figure out something that could work
app-wide on the webapp side.

and yes - this is separate from (though touches) the show polish sweep.
Different thread.
