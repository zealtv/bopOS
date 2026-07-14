#!/usr/bin/env python3
"""Focused checks for unprivileged node power controls."""

import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    REPO = os.path.dirname(REPO)
sys.path[:0] = [os.path.join(REPO, "python"), os.path.join(REPO, "python", "io")]

import pyOSC3  # noqa: E402


class FakeServer:
    def __init__(self, _target):
        pass

    def addMsgHandler(self, _address, _callback):
        pass

    def close(self):
        pass


class FakeClient:
    def connect(self, _target):
        pass

    def send(self, _message):
        pass


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["bopos.py", "unknown"]
import bopos  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def callback_checks():
    old_run, old_send = bopos.run_command, bopos.send_to_engine
    commands, notices = [], []
    try:
        bopos.run_command = lambda argv, **_kwargs: commands.append(tuple(argv)) or 0
        bopos.send_to_engine = lambda message: notices.append(message)
        check("reboot callback reports accepted authorization", bopos.reboot_callback() is True)
        check("shutdown callback reports accepted authorization", bopos.shutdown_callback() is True)
        expected = [
            ("/usr/bin/sudo", "-n", "/usr/bin/systemctl", "reboot"),
            ("/usr/bin/sudo", "-n", "/usr/bin/systemctl", "poweroff"),
        ]
        check("callbacks use only exact non-interactive commands", commands == expected,
              repr(commands))
        check("callbacks notify the engine before power action", len(notices) == 2)
        bopos.run_command = lambda _argv, **_kwargs: 1
        check("authorization failure is returned honestly", bopos.reboot_callback() is False)
    finally:
        bopos.run_command, bopos.send_to_engine = old_run, old_send


def policy_checks():
    policy_path = os.path.join(REPO, "systemd", "bopos-power.sudoers")
    with open(policy_path, encoding="utf-8") as source:
        rules = [line.strip() for line in source if line.strip() and not line.startswith("#")]
    expected = ("pi ALL=(root) NOPASSWD: /usr/bin/systemctl reboot, "
                "/usr/bin/systemctl poweroff")
    check("sudoers policy grants only the two power commands", rules == [expected], repr(rules))
    installer = open(os.path.join(REPO, "bash", "install-power-control.sh"),
                     encoding="utf-8").read()
    check("installer validates policy before and after installation",
          '"$VISUDO" -cf "$SOURCE"' in installer
          and 'as_root "$VISUDO" -cf /etc/sudoers' in installer)
    check("later unprivileged updates reuse installed authorization",
          "sudo -n -l /usr/bin/systemctl reboot" in installer
          and "sudo -n -l /usr/bin/systemctl poweroff" in installer)
    updater = open(os.path.join(REPO, "bash", "update.sh"), encoding="utf-8").read()
    check("fresh-node update installs power authorization",
          '"$SCRIPT_DIR/install-power-control.sh"' in updater)


def main():
    callback_checks()
    policy_checks()
    total = 9
    print("\n{}/{} passed".format(total - len(FAILURES), total))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
