"""Bounded subprocess execution. No shell, inherited stdin, or raw diagnostics."""

import subprocess  # nosec B404
import threading
import time
from pathlib import Path


class AudioError(Exception):
    """Safe internal error code; never includes paths, payloads or stderr."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def run_bounded(
    args: list[str],
    *,
    timeout: float,
    max_bytes: int,
    output: Path | None = None,
    cancel: threading.Event | None = None,
) -> bytes:
    """Drain both pipes; kill and reap on timeout/overflow/write failure.

    FFmpeg is executed directly and does not spawn child tools. A worker cancellation
    event kills/reaps the tool and drains its pipes before scratch cleanup.
    """
    captured = bytearray()
    failed = threading.Event()
    if cancel is not None and cancel.is_set():
        raise AudioError("AUDIO_CANCELLED")
    try:
        # Caller supplies the fixed tool argument list; shell execution stays disabled.
        with subprocess.Popen(  # nosec B603
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0,
        ) as proc:
            stdout, stderr = proc.stdout, proc.stderr
            if stdout is None or stderr is None:
                proc.kill()
                raise AudioError("AUDIO_PROCESS_IO")

            def stop() -> None:
                try:
                    proc.kill()
                except OSError:
                    # Already exited; wait below still reaps the process.
                    pass

            def drain_stdout() -> None:
                sink = None
                try:
                    if output is not None:
                        sink = output.open("xb")
                    count = 0
                    while block := stdout.read(65536):
                        count += len(block)
                        if count > max_bytes:
                            failed.set()
                            stop()
                            break
                        if sink is None:
                            captured.extend(block)
                        else:
                            sink.write(block)
                except OSError:
                    failed.set()
                    stop()
                finally:
                    if sink is not None:
                        try:
                            sink.close()
                        except OSError:
                            failed.set()

            def drain_stderr() -> None:
                # Discard immediately; a hostile input cannot fill memory/disk via logs.
                while stderr.read(65536):
                    pass

            readers = [threading.Thread(target=drain_stdout), threading.Thread(target=drain_stderr)]
            for reader in readers:
                reader.start()
            timed_out = False
            cancelled = False
            try:
                deadline = time.monotonic() + timeout
                while proc.poll() is None:
                    cancelled = cancel is not None and cancel.is_set()
                    timed_out = time.monotonic() >= deadline
                    if cancelled or timed_out:
                        stop()
                        proc.wait()
                        break
                    try:
                        proc.wait(timeout=min(0.05, max(0.001, deadline - time.monotonic())))
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                for reader in readers:
                    reader.join()
            if timed_out:
                raise AudioError("AUDIO_TIMEOUT")
            if cancelled or cancel is not None and cancel.is_set():
                raise AudioError("AUDIO_CANCELLED")
            if failed.is_set():
                raise AudioError("AUDIO_OUTPUT_LIMIT_OR_IO")
            if proc.returncode != 0:
                raise AudioError("AUDIO_PROCESS_FAILED")
    except FileNotFoundError:
        raise AudioError("AUDIO_BINARY_MISSING") from None
    except OSError:
        raise AudioError("AUDIO_PROCESS_IO") from None
    return bytes(captured)
