# Recommendation for Bob — stop upgrading the whole OS during device install

Recommend removing `apt-get upgrade -y` from install-device.sh and its manual
installation instructions in a separately approved change. Keep `apt-get update`
and installing the named prerequisites; handle system upgrades as deliberate
bench maintenance with an image/package record and audio/peripheral checks.

Why: an otherwise repeatable bopOS install can currently move JACK, Pd, kernel
or drivers along with every other installed package. Python pins do not prevent
that. Removing the full upgrade reduces unrelated movement, but named apt
packages would still resolve from the image's configured repositories; exact
OS repeatability needs an image/snapshot policy as a separate decision.

This changes what devices receive, so it is a recommendation, not implemented.
The installer and its manual apt-upgrade command remain unchanged. No node was
contacted. Current rig Pi OS, Pd/JACK and Python-package versions are unchecked;
docs/INSTALL.md gives Bob the read-only command to collect and compare them.
