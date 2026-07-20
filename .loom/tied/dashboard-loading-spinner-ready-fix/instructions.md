# dashboard-loading-spinner-ready-fix

Fix the initial-state race reported by Bob: a fast WebSocket can deliver its
one `state` message before the technical or facilitator app registers a state
handler, leaving the loading overlay permanently visible. Buffer unhandled
socket messages and drain them when a handler registers. Change the spinner
caption from "getting the room ready" to "loading..." on both pages. Verify an
immediate synchronous state is retained and the real pages still dismiss.
