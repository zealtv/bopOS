# Implementation decisions

- `PARAM_KINDS` is the declaration-to-wire mapping:
  `float→f`, `int→i`, `toggle→i`, `enum→i`, `text→s`.
- Show-document argument tags remain a local `ARG_TYPES = ("i", "f", "s")`
  grammar in `show_model.py`; they no longer depend on manifest declarations.
- The manifest editor strips derived toggle/enum bounds when saving. Enum
  options are authored one label per line, so commas remain legal inside a
  label.
- All runtime declaration consumers map `kind` back to the existing wire tag;
  no compatibility read of declaration `type` exists.
- The event declaration list and cue surfaces were left unchanged for children
  3 and 4.
