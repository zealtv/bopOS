# Kite Choir — SOH Northern Broadwalk site-plan handoff

Starting bopOS Seat/element layout for the 52-position Sydney Opera House Northern Broadwalk installation.

Source owner: `kite-choir-brains` lore
`2026-08-28-northern-broadwalk-bopos-site-plan`. The CSV was derived from
`docs/images/soh-northern-broadwalk-spatialisation-working-plan.svg` at exactly 14 drawing pixels per
metre.

## Coordinate contract

- router/Wi-Fi AP is `(0,0)`;
- `x_m` increases plan-right;
- `y_m` increases plan-down;
- `seat_id` is 0-based;
- one positioned element per spool, `element_index = 0`;
- `pole_height_m` is installation context, not an element coordinate.

The file contains 52 positions: 24 × 4 m poles and 28 × 3 m poles.

## Validation gate

This is a working vector translation, not an issued survey. Preserve the router-relative convention
when importing it into a bopOS venue snapshot, and validate final physical placement against the
issued Sydney Opera House operational drawing before deployment.

