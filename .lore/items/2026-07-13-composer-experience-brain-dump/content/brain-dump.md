# Brain dump — composer & patch-author experience (Bob, 2026-07-13, verbatim)

I'm looking at the current Bop OS web interface and considering what the patch author and composer experience is like.

A few sticking points that I can identify:
- The Pure Data patch, if the author is creating a Pure Data patch, requires BOPOS externals. If the author is working outside of the BOPOS file structure then those externals need to be brought in from somewhere. This makes me think that the workflow for developing a patch, be it pure data, super collider or other, should involve creating the patch inside the BOPOS directory structure. So each patch would be a folder inside the BOPOS patch folder. Some of these folders might be git repos, some might not be. If a project that is a Git repo is pushed to the device then that device should be able to update its patch without the Popos dashboard, i.e., with only an internet connection, being sent a pull patch message.This would sidestep the need for composers to get their head around git. They could, if they want, just build their patch on their machine with Bopos and then use Bopos to send that patch to the device in a similar fashion to sending media to the device.


- With an unassigned device by default when you assign it an ID, the name that's suggested should be pulled from its host name. I'm also noticing, at least in this example, the number box to increment or decrement the ID wouldn't let me increment or decrement. It kept resetting to six. by decrementing down to 3, i was then able to reincrement back up beyond 6 and set a new id

- The technical view should have the master slider visible somewhere, probably with the mute button.

- The aloha button on the technical view, I suspect, is no longer needed.

- I'd like a button back to the technical view from the facilitator page. If we need to set a way to lock the facilitator page we can find a mechanism to do that later.

- Get samples should be instead called Get Assets. - or possibly send assets. And thinking about this in the same vein as the pure data patch workflow, perhaps we need an assets folder in BOP OS and we choose a directory from that assets folder to send. It should overwrite the existing directory on the Pi if that directory already exists. I think the model here that is forming in my mind is that the directory structure on the Pi mirrors the directory structure of the computer hosting Bopos.


- The listener Heading should be able to be controlled by clicking and dragging the little circle on a line that is indicating the listener's heading. That should act kind of like a dial when you click and drag it. We can remove the listener heading and number box from the UI.

- The dots indicating the devices and elements shouldn't have their opacity changing in relation to points because there might be many points or there might be no points. A separate indicator, coloured to identify the point, perhaps a dashed circle could expand around that point, indicating the amplitude of it's associated coloured point.

- It would be good to be able to visualise the heartbeats of the devices in the bar on the left, give them a little blip when they beat.


- Regarding sending patches and media there are two potential approaches I could see:
    - Async patches and a sync media button or message, which would synchronise all patches on the BOPOS computer to the device or all devices.
    - A sync assets button, which would do the same thing, or a method to sync individual patches and individual folders of assets.

- Once patches are on the device then changing the patch should be able to be done via a drop down rather than typing the name of the patch. Maybe you can delete patches in this manner as well. In this sense being able to both sync all of the patches from the Bop OS conducting computer to all devices as well as send individual patches would make sense.

- It's a bit unclear what the Update All button does on the dashboard. It's unclear as to whether that updates Bop OS or it updates the current patch.

- Assets can simply be listed with some sort of metadata, like the number of files or the size of the folder and the date it was updated.


- It would be good to manage the simulated fleet from the BOPOS dashboard itself. For example on the left there could be a section for simulate and then you could add or remove devices. You should be able to send those device patches just like you send real device patches. And having some way to save the state of that simulated fleet would be useful.
note what was required to forget previous sims:
```
For the simulated devices, your current dashboard state contains five 02:53:49:4d:* simfleet nodes, three audition-* nodes, and
  the real bop000. There is currently no dashboard “forget device” button; discovered UIDs are persisted indefinitely.

  Stop the dashboard, simfleet, and audition rig, then from the Mac repo:

  cp dashboard/installation.json dashboard/installation.json.backup

  jq '.devices |= with_entries(
    select((.key | startswith("02:53:49:4d:") or startswith("audition-")) | not)
  )' dashboard/installation.json > /tmp/bopos-installation.json

  mv /tmp/bopos-installation.json dashboard/installation.json
```
Thinking about this a little bit further, I think it's simply a simulate button that simulates all nodes on the space and those nodes can either be positions of real BOP/OS devices or optionally virtual devices.
There's some workflow that needs to be thought about here I think because as a composer we might want to pre-arrange the space, pre-designate positions and IDs, and then later associate these positions and IDs with devices. We need a really clean and reliable way to do that. This might mean thinking about the data model or the model that we're using to think about devices as representations in BOP/OS and real devices and how that mapping occurs both locally and when we're deploying. This requires some UX forethought, some serious design consideration considering the composer's user experience. The composer can be thought of as the same person deploying the system in many or most cases.

- the listener puck only needs to be visible when simulation is active.  so there should be a button to enable/disable simulation.  some thought should be put into this

- When you change the size or speed of a point, it should not affect its position or trajectory. And currently the points draw themselves overlapping the bounds of the space. The points should be obscured beyond the bounds of the space.

- There should also be a list of points so you can select a point without needing to click it on the space because the points might be moving and they can be hard to click.

- I think as part of this brain dump and body of changes, a really important thing is going to be to have a document that very simply and clearly lays out for a composer:
    - how to create a patch
    - what they need running locally to be able to do that
    - step by step how to get that patch onto a device in a beautifully laid out, very simple, clearly labelled markdown file


- The synced cue section is in the wrong place. It's currently in the spatial section and that seems inappropriate. It should be further down somewhere.

- And the map should be at the top of the body of the web page. It's our primary view and then below that we have our user interface or blow into the sides but the map is that central overview where we can see what is happening.

- We should consider whether the boppos.config file is required inside a project and whether the project is required to be named main.pd rather than putting the name of the starting patch in the manifest.

- You know, as part of the pattern in what I've dumped here, rather than having a template's folder for Super Collider, Super Collider would simply be the demo Super Collider patch in the patches folder, akin to the demo PD patch in the patches folder (replacing "default")
