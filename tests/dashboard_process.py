"""Launch a real dashboard without borrowing an operator's listener ports.

Keep explicit private ports when a journey needs to address a listener. For
unused listeners, port 0 lets the kernel allocate a port at bind time, avoiding
the race between probing a free port and starting the child.
"""
import subprocess


LISTENER_DEFAULTS = {
    "--port": 5580,
    "--listen-port": 5550,
    "--stream-port": 5551,
    "--input-port": 5552,
    "--sim-io-listen-port": 8880,
}


def launch_dashboard(command, **kwargs):
    """Popen with private listener ports; preserve the caller's process handling."""
    command = list(command)
    # A managed audition process also binds send-port. It needs a known port
    # for commands, so journeys must supply one rather than use port 0.
    for option, default in {**LISTENER_DEFAULTS, "--send-port": 6660}.items():
        values = []
        for index, arg in enumerate(command):
            if arg == option:
                values.append(int(command[index + 1]))
            elif str(arg).startswith(option + "="):
                values.append(int(arg.split("=", 1)[1]))
        if default in values:
            raise ValueError(f"test dashboard cannot use default {option} {default}")
        if not values:
            if option == "--send-port":
                raise ValueError("test dashboard needs an explicit private --send-port")
            command.extend((option, "0"))
    return subprocess.Popen(command, **kwargs)
