"""Observe int/float OSC IDs through the unchanged framework patch in real Pd."""
import argparse
from pathlib import Path
import queue
import socket
import subprocess
import threading
import time

from pythonosc.osc_message_builder import OscMessageBuilder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pd", type=Path)
    args = parser.parse_args()
    root = next(path for path in Path(__file__).resolve().parents
                if (path / "tools/simfleet.py").exists())
    print(subprocess.check_output([str(args.pd), "-version"],
                                  stderr=subprocess.STDOUT, text=True).strip())
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.bind(("127.0.0.1", 0))
        port = sender.getsockname()[1]
    lines = queue.Queue()
    command = [str(args.pd), "-nogui", "-noaudio", "-stderr",
               "-path", str(root / "pd"), "-open", str(root / "pd/bopos~.pd"),
               "-send", f"BOPOS_ENGINE_PORT {port}"]
    print("Pd command:", command)
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)

    def read_output():
        for line in process.stdout:
            print(line.rstrip(), flush=True)
            lines.put(line.strip())

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        # Pd startup is bounded; repeated first packet avoids racing listen setup.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            for value in (0, 7, -1):
                observed = []
                for tag in ("f", "i"):
                    message = OscMessageBuilder(address="/id")
                    message.add_arg(value, arg_type=tag)
                    packet = message.build().dgram
                    expected = f"bopos-context: id {value}"
                    deadline = time.monotonic() + 5
                    while True:
                        assert process.poll() is None, "Pd exited before receiving /id"
                        sender.sendto(packet, ("127.0.0.1", port))
                        try:
                            line = lines.get(timeout=.2)
                        except queue.Empty:
                            line = ""
                        if line.startswith("bopos-context: id"):
                            assert line == expected, (tag, value, line)
                            observed.append(line)
                            break
                        assert time.monotonic() < deadline, (tag, value, "no context ID")
                    # Drain queued startup/retry output before the next distinct packet.
                    time.sleep(.1)
                    while not lines.empty():
                        lines.get_nowait()
                assert observed[0] == observed[1]
                print(f"PASS: /id {value} with f and i both yielded {observed[0]}", flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        reader.join(timeout=1)


if __name__ == "__main__":
    main()
