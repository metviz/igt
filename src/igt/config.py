from pathlib import Path
from typing import Mapping

from igt.errors import ConfigError

# src/igt/config.py -> repo root. ponytail: only meaningful for an editable/dev install;
# for a wheel install this points into site-packages, which is harmless.
REPO_ROOT = Path(__file__).resolve().parents[2]


def outside(path: Path, forbidden: Path, what: str) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == forbidden or forbidden in resolved.parents:
        raise ConfigError(
            f"{what} must not be inside the repository ({forbidden}): {resolved}"
        )
    return resolved


def env_path(env: Mapping[str, str], name: str, forbidden: Path) -> Path | None:
    value = env.get(name, "").strip()
    return outside(Path(value), forbidden, name) if value else None


def require_out_root(env: Mapping[str, str], forbidden: Path) -> Path:
    root = env_path(env, "IGT_OUT_ROOT", forbidden)
    if root is None:
        raise ConfigError(
            "IGT_OUT_ROOT is not set; export it to a directory outside the repo to use --out"
        )
    return root
