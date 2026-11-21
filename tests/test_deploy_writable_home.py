"""Read-only-root deployments must give the server a writable home directory.

Importing the server creates ``~/.simplenote_mcp/logs/metrics`` (``monitoring/metrics.py``)
and the alert log's directory beside it (``alerting.py``). Both use ``Path.home()``, which in
the image is ``HOME`` from the Dockerfile. ``docker-compose.yml`` (``read_only: true``) and the
Helm chart (``readOnlyRootFilesystem: true``) run the image on a read-only root, so unless
that home directory is a writable mount the server dies at import with
``OSError: [Errno 30] Read-only file system: '/home/mcp/.simplenote_mcp'``.
"""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHART_VALUES = REPO_ROOT / "helm" / "simplenote-mcp-server" / "values.yaml"


def _image_home() -> str:
    """Return the HOME the runtime image sets (the last ``ENV HOME=`` in the Dockerfile)."""
    homes = re.findall(
        r"^ENV HOME=(\S+)\s*$", (REPO_ROOT / "Dockerfile").read_text(), re.MULTILINE
    )
    assert homes, "the Dockerfile sets no ENV HOME, so this test can't tell which path"
    return homes[-1]


def _tmpfs_target(entry: object) -> str:
    """Return the container path of a Compose ``tmpfs:`` entry, ``PATH[:OPTIONS]``."""
    return str(entry).split(":", 1)[0]


def _volume_target(entry: object) -> str:
    """Return the container path of a Compose ``volumes:`` entry, short or long syntax.

    Short syntax is ``SOURCE:TARGET[:MODE]``; long syntax is a mapping with ``target``
    (which also covers ``type: tmpfs`` volumes).
    """
    if isinstance(entry, dict):
        return str(entry.get("target", ""))
    return str(entry).split(":")[1]


def test_image_home_is_absolute():
    assert _image_home().startswith("/")


def test_compose_read_only_services_mount_a_writable_home():
    home = _image_home()
    services = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())[
        "services"
    ]
    read_only = {name: svc for name, svc in services.items() if svc.get("read_only")}
    assert read_only, (
        "no read_only service in docker-compose.yml; this test checks nothing"
    )
    for name, svc in read_only.items():
        tmpfs = svc.get("tmpfs", [])
        tmpfs = [tmpfs] if isinstance(tmpfs, str) else tmpfs
        targets = {_tmpfs_target(t) for t in tmpfs}
        targets |= {_volume_target(v) for v in svc.get("volumes", [])}
        assert home in targets, (
            f"service {name!r} is read_only but mounts nothing writable at {home}"
        )


def test_chart_read_only_root_mounts_a_writable_home():
    home = _image_home()
    values = yaml.safe_load(CHART_VALUES.read_text())
    assert values["securityContext"]["readOnlyRootFilesystem"] is True, (
        "the chart no longer sets readOnlyRootFilesystem; revisit this test"
    )
    mounts = {m["mountPath"]: m["name"] for m in values.get("volumeMounts", [])}
    assert home in mounts, f"no volumeMount at {home}"
    volumes = {v["name"] for v in values.get("volumes", [])}
    assert mounts[home] in volumes, (
        f"volumeMount {mounts[home]!r} at {home} names no volume in values.volumes"
    )
