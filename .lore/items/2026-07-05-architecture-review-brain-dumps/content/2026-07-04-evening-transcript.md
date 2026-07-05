# Brain dump — evening 2026-07-04 (machine transcription, errors present)

Um, Which is being developing in the plants OS. Uh, repo. Which originally branched from
both OS and is now being pulled back into bopOS, Um, there's a lot of stuff that's
working quite well for us. Um, Ability to, Update. The Devices, remotely by pressing a
button and then pulling down git.

Repo is very effective. Um, the ability to store patches in the gate repo that whole
mechanism is working quite well. Um,

Some of the limitations that we are noticing, are Cpu overhead. Which I think is probably
Due to pure data. I'm running into single thread. And but itself, which has some
inefficiencies Keeping buff OS agnostic, as to, whether it's using pure data or not, I
think is probably important. And also tidying up.

The OSC schema, I think might be important. Things that I can see. Finally useful with.
Um, I Synchronised clock. Um, but these devices Uh, connected over Wi-Fi. And, Um, Lancy
can be an issue. If we're trying to do very tight synchronisation, Say some sort of
forward synchronised, clock would be very useful.

So we can trigger cues. Um, precisely. The other thing. That I can see being very useful
useful is being able to spatialize sound. And, The method that we've used. And on another
system. Is to start a sound playing simultaneously in all of the devices. And then
control. A radius moving through a space.

Um, or a point moving through a space. And using. A radius around that point to control
the gain on that sample. Um, or whatever it is that it's playing. Um, And so that that's
something that'll be quite useful.

And I guess what I'm wondering is. Um, Where do these things happen? Do they happen in
Bob OS itself. So they're agnostic to pure data. Or do they happen on the? Uh, patch
that's generating the audio. Um, My initial sense is that the forward synchronisation
could be handled by Papa West.

Um, and then Playback remains agnostic on the devices. Um, The other area of friction
that I'm noticing, is that if we're working with musicians, who aren't necessarily, Tech
savvy. Having them one work in pure data to upload a Patch to GitHub and then, Um need to
set up a wireless network and get the Raspberry Pi wireless network.

And then communicate to it over OC basically working with a headless device. Uh, provide
some technical challenges. I think that's a second, secondary. Concern. I can provide
some hand holding. Uh, is there is Friction at overhead there. Um, And then optimising,
the Raspberry Pi. Um, operating system for grow time, playback and finding Efficiencies
that we can find.

Splitting of different processes or running a different stack Etc. I'm also interested in
what other Frameworks, other than pure data. We could run. Um, Abs super glider but I'd
be interested if there's anything else. And then, Finally, the other thing that I'm
noticing is audio input. But this might be a hardware consideration.

Uh, we often arrive. Dgm plus boards which give us Amplified audio out. But no audio in
And bubble West, as it's currently configured. Um, Sets up Jack with stereo out. Um, And
so, I guess the gist of everything is Uh, Specific features being a forward, synchronised
clock. Um, Are fine.

Don't say, schema. Uh, flexible and lower friction. Patch creation. Um, And the other
things that I noted, Potentially audio input. Uh, basically I'm looking for a review of
bubble West itself. Um, and and Smoothing out that setup. Uploading. Maintenance. Um,
process. Um, As a lot of what we have running at the moment does work and it does work
relatively well.
