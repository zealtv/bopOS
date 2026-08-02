# Decisions

## Commit gesture

Text fields commit on **Enter and blur**. Enter is the deliberate keyboard
commit and releases focus; blur preserves the normal form-control path. A
remembered committed value prevents Enter followed by blur from sending the
same OSC string twice. IME composition Enter is ignored.

This matches the nearest shipped idiom, `PrecisionField`: Enter commits and
leaving the editor commits. The text control stays a native text input rather
than adopting PrecisionField's temporary-editor swap.

## Mixed aggregate

Keep the existing visible word `mixed` and add the ratified 45-degree mixed
hatch to the field. Numeric boxes use dots because they have a compact numeric
face; a free-form text field can state the condition directly. Its accessible
name continues to say “mixed values.” Editing any value, including the empty
string, clears the mixed state and unifies the target.

Text has no generator, so there is no cyan mixed-generator variant.

## Maximum length

No manifest `maxLength` is added. The ratified text grammar has no such field,
the existing OSC string path does not expose a patch-level limit, and no patch
requirement supplies a meaningful bound. Adding one here would change the
manifest contract to solve an unmeasured UI concern. A transport-wide safety
bound, if one becomes necessary, belongs at the protocol/server boundary and
should be designed consistently for every string sender.

## Component ownership

The row uses `text` end-to-end (`live-param-text`) rather than the UI-only
alias `string`. Its appearance is anchored on that row root, not on its
Control/Device/Remote/editor hosts, so the component travels intact.
