"""Review-only shell reproductions. No sudo, installers, real mounts or audio.

Writes only below /tmp and this stitch (when output is redirected there).
Two hardware predicates in copied sources are replaced with fixture predicates:
/proc/asound/cards -> fixture file; USB block-device check -> regular-file check.
The boot-service case replaces process-substitution log sinks with ordinary
fixture files, because the macOS sandbox denies /dev/fd redirection. Launch,
exit-status handling and ordering are unchanged.
"""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time

REPO = next(p for p in Path(__file__).resolve().parents if (p / "install-device.sh").exists())


def script(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)


def invoke(root, relative, args=(), extra=None):
    env = dict(os.environ, PATH=str(root / "bin") + ":" + os.environ["PATH"],
               PYTHONDONTWRITEBYTECODE="1")
    env.update(extra or {})
    log = root / "output.log"
    with log.open("w") as stream:
        result = subprocess.run(["bash", str(root / relative), *args], env=env,
                                stdout=stream, stderr=subprocess.STDOUT, timeout=10)
    # The copied launcher can exit before the deliberately failing background
    # engine writes its diagnostic; give that fixture child time to exit.
    time.sleep(0.1)
    return result.returncode, log.read_text()


def engine_case(mode):
    with tempfile.TemporaryDirectory(prefix="bopos-74-3-", dir="/tmp") as tmp:
        root = Path(tmp)
        for folder in ("bash", "bin", "patches/live", "python", "run"):
            (root / folder).mkdir(parents=True)
        (root / "patches/active_patch.txt").write_text("live\n")
        (root / "cards").write_text("DigiAMP\n")
        source = (REPO / "bash/start-engine.sh").read_text()
        source = source.replace("/proc/asound/cards", str(root / "cards"))
        script(root / "bash/start-engine.sh", source)
        script(root / "bin/python3", '''#!/bin/bash
case "$1" in
  */manifest.py) printf "ENGINE='pd'\\nENTRYPOINT='entry.pd'\\n" ;;
  */runcontext.py)
    if [ "$CASE" = context ]; then echo 'fixture context failure' >&2; exit 42; fi
    printf "BOPOS_SEED='123'\\nBOPOS_RUN_ID='fixture'\\n" ;;
  */audio_config.py)
    if [ "$CASE" = audio ]; then echo 'fixture record-active failure' >&2; exit 43; fi ;;
esac
''')
        script(root / "bin/jackd", "#!/bin/bash\nexec /bin/sleep 60\n")
        script(root / "bin/jack_lsp", "#!/bin/bash\nexit 0\n")
        script(root / "bin/pd", "#!/bin/bash\necho 'fixture engine exits 87' >&2\nexit 87\n")
        try:
            rc, output = invoke(root, "bash/start-engine.sh", extra={"CASE": mode})
            for _ in range(30):
                output = (root / "output.log").read_text()
                if "fixture engine exits 87" in output:
                    break
                time.sleep(0.1)
            assert rc == 0, (rc, output)
            assert (root / "run/engine.pid").exists()
            if mode == "context":
                assert "fixture context failure" in output and "RUN ID: fallback-" in output
            elif mode == "audio":
                assert "fixture record-active failure" in output
            else:
                assert "fixture engine exits 87" in output, output
            print(f"CONFIRMED engine/{mode}: launcher exit={rc}; failed dependency/engine accepted")
        finally:
            # Only the inert JACK process launched by this fixture is signalled.
            path = root / "run/jackd.pid"
            if path.exists():
                try:
                    os.kill(int(path.read_text()), signal.SIGTERM)
                except ProcessLookupError:
                    pass


def stale_pid():
    with tempfile.TemporaryDirectory(prefix="bopos-74-3-", dir="/tmp") as tmp:
        root = Path(tmp)
        (root / "run").mkdir()
        script(root / "bash/stop-engine.sh", (REPO / "bash/stop-engine.sh").read_text())
        # Valid recorded engine PID skips unsafe name-wide fallback.
        unrelated = subprocess.Popen(["/bin/sleep", "60"])
        (root / "run/engine.pid").write_text(str(unrelated.pid))
        (root / "run/engine.name").write_text("a-different-engine")
        # Unused stale legacy records avoid any real pkill fallback too.
        for name in ("pd", "jackd"):
            (root / f"run/{name}.pid").write_text("99999999")
        waiter = threading.Thread(target=unrelated.wait)
        waiter.start()
        try:
            rc, output = invoke(root, "bash/stop-engine.sh")
            waiter.join(timeout=2)
            assert rc == 0 and unrelated.returncode == -signal.SIGTERM, (rc, output)
            print("CONFIRMED stale PID: unrelated fixture sleep killed despite engine.name mismatch")
        finally:
            if unrelated.poll() is None:
                unrelated.terminate()
            unrelated.wait()
            waiter.join()


def usb_ownership():
    with tempfile.TemporaryDirectory(prefix="bopos-74-3-", dir="/tmp") as tmp:
        root = Path(tmp)
        (root / "bin").mkdir()
        (root / "sdb1").touch()
        (root / "mounted").write_text("sda1")
        text = (REPO / "bash/bopos-usb-mount").read_text()
        text = text.replace('MOUNT_POINT="/media/bopos-usb"', f'MOUNT_POINT="{root}/mount"')
        text = text.replace('local dev="/dev/${devname}"', f'local dev="{root}/${{devname}}"')
        text = text.replace('[ ! -b "$dev" ]', '[ ! -f "$dev" ]')
        script(root / "bash/bopos-usb-mount", text)
        script(root / "bin/mountpoint", f'#!/bin/bash\ntest -f "{root}/mounted"\n')
        script(root / "bin/umount", f'#!/bin/bash\n/bin/rm "{root}/mounted"\n')
        rc, output = invoke(root, "bash/bopos-usb-mount", ["mount", "sdb1"])
        assert rc == 0 and "already mounted; ignoring" in output
        # Exactly the argument-less ExecStop of bopos-usb@sdb1.service.
        rc, output = invoke(root, "bash/bopos-usb-mount", ["unmount"])
        assert rc == 0 and not (root / "mounted").exists()
        print("CONFIRMED USB: ignored sdb1 start succeeds; its stop unmounts sda1 fixture")


def boot_service_exit():
    with tempfile.TemporaryDirectory(prefix="bopos-74-3-", dir="/tmp") as tmp:
        root = Path(tmp)
        (root / "python/io").mkdir(parents=True)
        text = (REPO / "bash/start.sh").read_text()
        for name in ("bopos", "io"):
            text = text.replace(f'> >(log_to "$RUN_DIR/{name}.log")',
                                f'> "$RUN_DIR/{name}.log"')
        script(root / "bash/start.sh", text)
        script(root / "bash/start-engine.sh", "#!/bin/bash\nexit 0\n")
        script(root / "bin/ip", "#!/bin/bash\necho '1.1.1.1 dev fixture'\n")
        script(root / "bin/python3", "#!/bin/bash\nexit 86\n")
        # start.sh prefers this venv over python3; both services and log sinks
        # fail here. HOME is supplied only as the child fixture's normal home.
        script(root / "home/venv/bin/python", "#!/bin/bash\necho 'fixture service exits 86'\nexit 86\n")
        rc, output = invoke(root, "bash/start.sh", extra={"HOME": str(root / "home")})
        assert rc == 0, (rc, output)
        assert (root / "run/bopos.pid").exists() and (root / "run/io.pid").exists()
        for name in ("bopos", "io"):
            assert "fixture service exits 86" in (root / f"run/{name}.log").read_text(), (name, output, (root / f"run/{name}.log").read_text())
        print("CONFIRMED boot: both service commands exit 86; start.sh still returns 0")


def privilege_source_audit():
    unit = (REPO / "systemd/bopos-usb@.service").read_text()
    provision = (REPO / "bash/provision.sh").read_text()
    assert "User=" not in unit and "Group=" not in unit
    assert "ExecStart=/home/pi/bopOS/bash/bopos-usb-mount mount %I" in unit
    assert 'chown -R pi:pi "$BOPOS_DIR"' in provision
    print("CONFIRMED source trust chain: USB unit defaults to root and executes pi-owned checkout helper")


if __name__ == "__main__":
    for mode in ("engine", "context", "audio"):
        engine_case(mode)
    stale_pid()
    usb_ownership()
    boot_service_exit()
    privilege_source_audit()
