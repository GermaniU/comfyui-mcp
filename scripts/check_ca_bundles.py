"""Fail if the distrusted emSign ECC Root CA - G3 is trusted anywhere in an image.

GHSA-6q48-6c7w-9gw2: intermediates under this root were compromised. Version
floors (pip, certifi, ca-certificates) are not enough on their own: a bundle can
be vendored, copied or left behind by a base image. This check matches the
certificate by the SHA-256 of its DER encoding, so it also catches PEM files
without labels (OpenSSL capath, vendored bundles).

Run inside the image, offline and as root so no file is skipped:

    docker run --rm --network none --user 0 --entrypoint python \\
        -v "$PWD/scripts/check_ca_bundles.py:/tmp/check_ca_bundles.py:ro" \\
        IMAGE /tmp/check_ca_bundles.py

Exit status is 1 if G3 is found, or if a bundle that must exist is missing or
suspiciously small (so the check cannot pass vacuously).
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import ssl
import sys

# SHA-256 of the DER of "emSign ECC Root CA - G3" (eMudhra).
G3_SHA256 = "86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b"

PEM = re.compile(
    rb"-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----", re.DOTALL
)
SKIP_DIRS = {"/proc", "/sys", "/dev"}
MAX_FILE = 5_000_000
MIN_ROOTS = 50  # every real root bundle carries well over this many certs


def fingerprints(data: bytes) -> set[str]:
    out = set()
    for match in PEM.finditer(data):
        try:
            der = base64.b64decode(b"".join(match.group(1).split()))
        except ValueError:
            continue
        out.add(hashlib.sha256(der).hexdigest())
    return out


def read(path: str) -> bytes | None:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def required_bundles() -> dict[str, str]:
    bundles = {}
    import certifi

    bundles["certifi"] = certifi.where()
    try:
        from pip._vendor import certifi as pip_certifi
    except ImportError:
        pass
    else:
        bundles["pip._vendor.certifi"] = pip_certifi.where()
    cafile = ssl.get_default_verify_paths().cafile
    bundles["system (OpenSSL cafile)"] = cafile or "/etc/ssl/certs/ca-certificates.crt"
    return bundles


def main() -> int:
    failures = []

    for label, path in required_bundles().items():
        data = read(path)
        fps = fingerprints(data) if data is not None else set()
        print(f"{label}: {path} ({len(fps)} certs)")
        if len(fps) < MIN_ROOTS:
            failures.append(f"{label}: missing or too small ({path})")
        if G3_SHA256 in fps:
            failures.append(f"{label}: G3 present ({path})")

    loaded = ssl.create_default_context().get_ca_certs(binary_form=True)
    loaded_fps = {hashlib.sha256(der).hexdigest() for der in loaded}
    print(f"ssl.create_default_context(): {len(loaded_fps)} certs loaded")
    if G3_SHA256 in loaded_fps:
        failures.append("ssl.create_default_context(): G3 loaded")

    # Every other PEM on the file system (capath, vendored bundles, leftovers).
    scanned = 0
    for dirpath, dirnames, filenames in os.walk("/"):
        if dirpath in SKIP_DIRS:
            dirnames[:] = []
            continue
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                if os.path.islink(path) or os.path.getsize(path) > MAX_FILE:
                    continue
            except OSError:
                continue
            data = read(path)
            if not data or b"BEGIN CERTIFICATE" not in data:
                continue
            scanned += 1
            if G3_SHA256 in fingerprints(data):
                failures.append(f"file system: G3 present in {path}")
    print(f"file system: {scanned} files with PEM certificates scanned")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1
    print("OK: emSign ECC Root CA - G3 is not trusted anywhere in this image")
    return 0


if __name__ == "__main__":
    sys.exit(main())
