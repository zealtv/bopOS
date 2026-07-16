# Device alias word-list review

Generator v1 is deliberately pinned product copy. This artifact makes the
complete vocabulary inspectable and records the scope of its language review.

Bob's ratified human direction is the review boundary: `Freda Sparks` sets the
tone; names are global, short, ASCII-only and easy to pronounce in English;
the second words are vivid non-name words with pop-star energy. The vocabulary
below was manually checked against those constraints during implementation.
That is not a claim that Bob approved every token individually. Any later word
change therefore requires a new generator version rather than silently
renaming devices already stored in the registry.

## Given names (64)

`Freda`, `Amara`, `Amina`, `Anya`, `Asha`, `Ayla`, `Bayo`, `Ciro`,
`Dalia`, `Diego`, `Eira`, `Elif`, `Enzo`, `Esme`, `Farah`, `Hana`,
`Hugo`, `Imani`, `Ines`, `Ivo`, `Jaya`, `Juno`, `Kaito`, `Kenji`,
`Kira`, `Lani`, `Leila`, `Lila`, `Lior`, `Luca`, `Mala`, `Malik`,
`Mara`, `Mateo`, `Mina`, `Mira`, `Miro`, `Nala`, `Nia`, `Niko`,
`Noor`, `Omar`, `Orla`, `Pavel`, `Priya`, `Rami`, `Ravi`, `Remy`,
`Rina`, `Rosa`, `Sami`, `Sana`, `Sora`, `Talia`, `Tariq`, `Theo`,
`Tova`, `Uma`, `Vera`, `Yara`, `Yuki`, `Zain`, `Zola`, `Zuri`.

## Character words (64)

`Sparks`, `Bloom`, `Comet`, `Echo`, `Halo`, `Neon`, `Orbit`, `Pepper`,
`Prism`, `Rocket`, `Tempo`, `Velvet`, `Breeze`, `Chrome`, `Cloud`, `Copper`,
`Coral`, `Dancer`, `Dusk`, `Ember`, `Falcon`, `Flash`, `Frost`, `Glow`,
`Gold`, `Groove`, `Harbor`, `Honey`, `Indigo`, `Jazz`, `Kite`, `Laser`,
`Lotus`, `Lunar`, `Maple`, `Melody`, `Mist`, `Moon`, `Moss`, `Nova`,
`Onyx`, `Peach`, `Pearl`, `Pixel`, `Pulse`, `Quartz`, `Rain`, `Reef`,
`Ribbon`, `River`, `Satin`, `Scout`, `Shine`, `Silver`, `Solar`, `Sonic`,
`Star`, `Storm`, `Sugar`, `Tiger`, `Vinyl`, `Wave`, `Willow`, `Zephyr`.

## Manual review checklist

- Both lists contain 64 distinct entries and preserve `Freda` / `Sparks` at
  index zero.
- Every token uses only ASCII letters, is between 2 and 12 characters, and
  produces a valid two-word alias with every token in the other list.
- Given names are drawn across several language traditions while remaining
  readily pronounceable for an English-speaking operator.
- Character words are concrete, memorable stage-name vocabulary rather than
  conventional family names; none contains punctuation or diacritics.
- The persisted resolved alias remains authoritative, so this review does not
  make future vocabulary edits safe within generator v1.
