#!/bin/bash
#
# install-device.sh — install or refresh bopOS on a Raspberry Pi device.
#
# Run as the normal `pi` user, not as root. The script asks for sudo only for
# system packages and bopOS's narrow privileged provisioning step.
#
# Optional overrides:
#   BOPOS_REPO_URL=https://github.com/zealtv/bopOS.git
#   BOPOS_BRANCH=main
#   BOPOS_LOCALE=en_AU.UTF-8
set -Eeuo pipefail

REPO_URL="${BOPOS_REPO_URL:-https://github.com/zealtv/bopOS.git}"
BRANCH="${BOPOS_BRANCH:-main}"
DEVICE_LOCALE="${BOPOS_LOCALE:-en_AU.UTF-8}"
BOPOS_DIR="$HOME/bopOS"
VENV="$HOME/venv"

usage() {
    sed -n '2,/^set -Eeuo pipefail$/s/^# \{0,1\}//p' "$0"
}

case "${1:-}" in
    -h|--help)
        usage
        exit 0
        ;;
    "")
        ;;
    *)
        echo "install-device.sh: unknown option '$1' (try --help)" >&2
        exit 2
        ;;
esac

if [ "$(id -u)" -eq 0 ]; then
    echo "install-device.sh: run this as the pi user, not with sudo." >&2
    exit 1
fi
if [ "$(id -un)" != "pi" ]; then
    echo "install-device.sh: this release expects the Raspberry Pi user to be named 'pi'." >&2
    echo "Reflash with that username or follow docs/INSTALL.md's manual path." >&2
    exit 1
fi
if [ "$(uname -s)" != "Linux" ] || [ ! -r /proc/device-tree/model ]; then
    echo "install-device.sh: this installer is for Raspberry Pi OS devices." >&2
    exit 1
fi

echo "==> Checking sudo access"
sudo -v

echo "==> Preparing Raspberry Pi OS"
sudo raspi-config nonint do_expand_rootfs
sudo raspi-config nonint do_i2c 0
sudo env LANG=C LC_ALL=C apt-get update
sudo env LANG=C LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
echo "jackd2 jackd/tweak_rt_limits boolean true" |
    sudo debconf-set-selections
sudo env LANG=C LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get install -y \
    alsa-utils jackd2 puredata git python3-pip python3-venv i2c-tools locales \
    build-essential python3-dev swig

# adafruit-blinka pulls in lgpio, RPi.GPIO and rpi_ws281x behind Raspberry Pi
# platform markers. lgpio ships aarch64 wheels for cp39-cp312 only, and
# piwheels serves armhf only, so on 64-bit Pi OS (Trixie is Python 3.13) pip
# compiles it — and that build needs swig. Measured on Trixie Lite 2026-08-10:
# build-essential and python3-dev were already present and swig was not, but
# all three are named here so the build does not depend on that. liblgpio-dev
# lets the build link the system library; it is absent before Bookworm, so it
# is optional.
sudo env LANG=C LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get install -y \
    liblgpio-dev ||
    echo "    (liblgpio-dev unavailable on this release; building lgpio from source)"

echo "==> Configuring system locale: $DEVICE_LOCALE"
sudo raspi-config nonint do_change_locale "$DEVICE_LOCALE"
# LANG is the ordinary default. Remove global LC_ALL/LANGUAGE overrides so
# shells, Python, and systemd can apply that default without precedence traps.
sudo update-locale LANG="$DEVICE_LOCALE" LC_ALL LANGUAGE
export LANG="$DEVICE_LOCALE"
unset LC_ALL LANGUAGE

if [ -e "$BOPOS_DIR" ] && [ ! -d "$BOPOS_DIR/.git" ]; then
    echo "install-device.sh: $BOPOS_DIR exists but is not a Git checkout." >&2
    echo "Move it aside, then rerun." >&2
    exit 1
fi

if [ ! -d "$BOPOS_DIR/.git" ]; then
    echo "==> Cloning bopOS into $BOPOS_DIR"
    git clone --branch "$BRANCH" --recursive "$REPO_URL" "$BOPOS_DIR"
else
    echo "==> Updating the existing bopOS checkout"
    git -C "$BOPOS_DIR" pull --ff-only --recurse-submodules
    git -C "$BOPOS_DIR" submodule sync --recursive
    git -C "$BOPOS_DIR" submodule update --init --recursive
fi

if [ ! -d "$VENV" ]; then
    echo "==> Creating device virtualenv at $VENV"
    python3 -m venv "$VENV"
else
    echo "==> Reusing device virtualenv at $VENV"
fi

echo "==> Installing device Python dependencies"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$BOPOS_DIR/python/requirements.txt"

echo "==> Installing device defaults and boot service"
sudo "$BOPOS_DIR/bash/provision.sh"

echo
echo "bopOS device installation is complete."
echo "Review $BOPOS_DIR/bopos.config if this device does not use a DigiAMP+."
echo "Rebooting now; this session will disconnect."
sudo systemctl reboot
