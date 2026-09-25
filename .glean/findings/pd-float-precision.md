# Keep large numbers and absolute time out of Pd

When a value travels to Pure Data over OSC, it must fit a 32-bit float — six significant figures at most.

Never send epoch timestamps or fine clocks to Pd as floats. Encode 64-bit values as strings or int pairs, and keep absolute time out of Pd entirely: nodes convert shared time to a local monotonic deadline and send Pd the bare event at fire time.

## Triggers

- float precision
- epoch
- timestamp

## Associations

- [[never-edit-pd]]
- [[osc-contract]]
