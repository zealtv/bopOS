# dashboard-tab-order-show-first

Apply the clean-slate UI/UX recommendation Bob accepted on 2026-07-20:

**Show · Dashboard · Seats · Devices · Patches · Assets**

- Make Show the first and default tab, matching its current role as the primary
  structured performance surface.
- Keep the label **Dashboard** for now.
- Preserve the existing tab IDs, hashes, panels, accessibility relationships,
  keyboard behavior, and narrow-screen scrolling.
- Update current operator documentation that enumerates the tabs.

Verify initial HTML/JS state, direct hash navigation, click navigation, arrow
key order, and compact rendering in a real browser. Keep the broader Dashboard
/ facilitator / manifest terminology question out of this implementation; Bob
requested a separate waiting design stitch after this work is tied.
