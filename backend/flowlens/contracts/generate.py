"""Deterministic schemas, examples validation and OpenAPI drift checks."""

import argparse
import json
from pathlib import Path
from typing import Any

from flowlens.api.app import create_app
from flowlens.contracts.models import INTERNAL_MODELS, PUBLIC_MODELS


def render(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def generate(root: Path, *, check: bool = False) -> bool:
    outputs = {
        root / "contracts/openapi/baseline.json": render(create_app(profile="test").openapi())
    }
    for visibility, models in (("public", PUBLIC_MODELS), ("internal", INTERNAL_MODELS)):
        for model in models:
            outputs[root / "contracts/json-schema" / visibility / f"{model.__name__}.json"] = (
                render(model.model_json_schema())
            )
    if check:
        return all(
            path.is_file() and path.read_text() == content for path, content in outputs.items()
        )
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if not generate(args.root, check=args.check):
        raise SystemExit("Contract drift detected; regenerate and review changes.")


if __name__ == "__main__":
    main()
