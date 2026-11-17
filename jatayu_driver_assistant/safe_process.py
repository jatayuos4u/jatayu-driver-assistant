"""Bounded read-only process execution; never use a shell or elevated privileges."""
import os
import selectors
import subprocess
import time

DEFAULT_LIMIT = 256 * 1024


def bounded_run(args, *, timeout=5, max_output_bytes=DEFAULT_LIMIT,
                capture_output=True, text=True, check=False, shell=False, **kwargs):
    """Capture at most max_output_bytes total; kill child on overflow or timeout.

    Return CompletedProcess like subprocess.run. Nonzero returncode 125 means
    output was truncated; callers MUST NOT consider that a successful scan.
    """
    if shell or not isinstance(args, (list, tuple)) or not args or any(not isinstance(a, str) for a in args):
        raise ValueError('Only fixed argument vectors without a shell are supported')
    if not capture_output or not text or check:
        raise ValueError('Bounded execution requires capture_output=True, text=True, check=False')
    if not isinstance(max_output_bytes, int) or not 4096 <= max_output_bytes <= 2 * 1024 * 1024:
        raise ValueError('Invalid capture bound')
    if not 0 < timeout <= 60:
        raise ValueError('Invalid timeout')
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            shell=False, stdin=subprocess.DEVNULL, **kwargs)
    streams = {proc.stdout: bytearray(), proc.stderr: bytearray()}
    total = 0
    cutoff = time.monotonic() + timeout
    selector = selectors.DefaultSelector()
    try:
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ)
        while selector.get_map():
            remaining = cutoff - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(args, timeout)
            for key, _ in selector.select(min(remaining, 0.2)):
                chunk = os.read(key.fileobj.fileno(), min(65536, max_output_bytes - total + 1))
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                total += len(chunk)
                if total > max_output_bytes:
                    proc.kill()
                    proc.wait()
                    return subprocess.CompletedProcess(args, 125, '', 'Diagnostic output limit reached')
                streams[key.fileobj].extend(chunk)
            if proc.poll() is not None and not selector.get_map():
                break
        remaining = cutoff - time.monotonic()
        proc.wait(timeout=max(0.001, remaining))
        return subprocess.CompletedProcess(args, proc.returncode,
            streams[proc.stdout].decode('utf-8', 'replace'),
            streams[proc.stderr].decode('utf-8', 'replace'))
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise
    finally:
        selector.close()
        for stream in streams:
            stream.close()
