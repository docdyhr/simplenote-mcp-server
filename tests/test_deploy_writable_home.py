"""Read-only-root deployments must give the server a writable home directory.

Importing the server creates ``~/.simplenote_mcp/logs/metrics`` (``monitoring/metrics.py``),
and the first alert writes its log beside it (``alerting.py``). Both use ``Path.home()``,
which in the image is ``HOME`` from the Dockerfile unless the deployment overrides it.
``docker-compose.yml`` (``read_only: true``) and the Helm chart
(``readOnlyRootFilesystem: true``) run the image on a read-only root, so unless that home
directory is a writable mount the server dies at import with
``OSError: [Errno 30] Read-only file system: '/home/mcp/.simplenote_mcp'``.
"""

import re
from pathlib import Path

import pytest
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


def _compose_env_home(environment: dict | list | None) -> str | None:
    """Return HOME from a Compose ``environment:`` list (``NAME=value``) or mapping."""
    if isinstance(environment, dict):
        value = environment.get("HOME")
        return None if value is None else str(value)
    for item in environment or []:
        name, sep, value = str(item).partition("=")
        if name == "HOME" and sep:
            return value
    return None


def _compose_writable_targets(service: dict) -> set[str]:
    """Return the container paths a Compose service mounts writable.

    ``tmpfs:`` entries are ``PATH[:OPTIONS]``; one whose options include ``ro`` doesn't
    count. ``volumes:`` entries are short syntax, ``[SOURCE:]TARGET[:MODE]``, or long
    syntax, a mapping with ``target`` and ``read_only`` (``type: tmpfs`` included).
    """
    targets = set()
    tmpfs = service.get("tmpfs", [])
    for entry in [tmpfs] if isinstance(tmpfs, str) else tmpfs:
        path, _, options = str(entry).partition(":")
        if "ro" not in options.split(","):
            targets.add(path)
    for entry in service.get("volumes", []):
        if isinstance(entry, dict):
            if not entry.get("read_only"):
                targets.add(str(entry.get("target", "")))
            continue
        parts = str(entry).split(":")
        if len(parts) == 1:
            target, mode = parts[0], ""
        elif len(parts) == 2:
            # SOURCE:TARGET, or TARGET:MODE when the second field isn't a path.
            target, mode = (
                (parts[1], "") if parts[1].startswith("/") else (parts[0], parts[1])
            )
        else:
            target, mode = parts[1], parts[2]
        if "ro" not in mode.split(","):
            targets.add(target)
    return targets


def _chart_writable_mounts(values: dict) -> set[str]:
    """Return mount paths backed by an emptyDir or PVC volume and not mounted readOnly."""
    writable_volumes = {
        v["name"]
        for v in values.get("volumes", [])
        if "emptyDir" in v or "persistentVolumeClaim" in v
    }
    return {
        m["mountPath"]
        for m in values.get("volumeMounts", [])
        if m.get("name") in writable_volumes and not m.get("readOnly")
    }


@pytest.mark.parametrize(
    ("service", "writable"),
    [
        ({"tmpfs": ["/home/mcp:rw,noexec,size=50m,uid=1000"]}, True),
        ({"tmpfs": "/home/mcp"}, True),
        ({"tmpfs": ["/home/mcp:ro"]}, False),
        ({"volumes": ["/home/mcp"]}, True),
        ({"volumes": ["home:/home/mcp"]}, True),
        ({"volumes": ["./home:/home/mcp:rw"]}, True),
        ({"volumes": ["./home:/home/mcp:ro"]}, False),
        ({"volumes": ["/home/mcp:ro"]}, False),
        ({"volumes": [{"type": "tmpfs", "target": "/home/mcp"}]}, True),
        (
            {
                "volumes": [
                    {
                        "type": "volume",
                        "source": "h",
                        "target": "/home/mcp",
                        "read_only": True,
                    }
                ]
            },
            False,
        ),
        ({"volumes": ["./logs:/app/simplenote_mcp/logs"]}, False),
    ],
)
def test_compose_writable_target_parsing(service, writable):
    assert ("/home/mcp" in _compose_writable_targets(service)) is writable


@pytest.mark.parametrize(
    ("volume", "mount_extra", "writable"),
    [
        ({"emptyDir": {}}, {}, True),
        ({"persistentVolumeClaim": {"claimName": "home"}}, {}, True),
        ({"emptyDir": {}}, {"readOnly": True}, False),
        ({"configMap": {"name": "home"}}, {}, False),
    ],
)
def test_chart_writable_mount_parsing(volume, mount_extra, writable):
    values = {
        "volumes": [{"name": "home", **volume}],
        "volumeMounts": [{"name": "home", "mountPath": "/home/mcp", **mount_extra}],
    }
    assert ("/home/mcp" in _chart_writable_mounts(values)) is writable


def test_image_home_is_absolute():
    assert _image_home().startswith("/")


def test_compose_read_only_services_mount_a_writable_home():
    services = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())[
        "services"
    ]
    read_only = {name: svc for name, svc in services.items() if svc.get("read_only")}
    assert read_only, (
        "no read_only service in docker-compose.yml: if that's deliberate, this test "
        "no longer applies and should go with it"
    )
    for name, svc in read_only.items():
        home = _compose_env_home(svc.get("environment")) or _image_home()
        assert home in _compose_writable_targets(svc), (
            f"service {name!r} is read_only but mounts nothing writable at {home}"
        )


def test_chart_read_only_root_mounts_a_writable_home():
    values = yaml.safe_load(CHART_VALUES.read_text())
    assert values["securityContext"]["readOnlyRootFilesystem"] is True, (
        "the chart no longer sets readOnlyRootFilesystem: if that's deliberate, this "
        "test no longer applies and should go with it"
    )
    home = (values.get("configMap", {}).get("data") or {}).get("HOME") or _image_home()
    assert home in _chart_writable_mounts(values), (
        f"no writable volumeMount (emptyDir or PVC, not readOnly) at {home}"
    )
