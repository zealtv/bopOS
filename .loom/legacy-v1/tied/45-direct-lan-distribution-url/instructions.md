# 45-direct-lan-distribution-url

Fix localhost-originated patch and asset distribution on a Mac whose tunnel
advertises the installation subnet.

- Reuse the direct-LAN-first `SO_DONTROUTE` source probe introduced for OSC in
  `54ff063` when `Dashboard.public_url()` derives an IPv4 node-fetch URL.
- Preserve explicit `--public-url`, non-loopback browser hosts, loopback nodes,
  routed-venue fallback, and IPv6 behavior.
- Add living coverage to `tests/test_osc_transport.py`.
- Verify the helper selects `192.168.0.100`, not Tailscale
  `100.113.184.66`, for Imani Silver at `192.168.0.103`.

Do not change the Pi's Tailscale configuration or any `.pd` file.
