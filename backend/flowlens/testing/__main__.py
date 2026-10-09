"""Run an isolated contract smoke; no servers, providers or permanent DB."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal, cast

from flowlens.contracts.models import JobResult, RequestContext, SourceEvent, TranscriptSegment
from flowlens.testing.harness import FakePlatform, SQLiteHarness, build_harness


def main() -> None:
    parser = argparse.ArgumentParser(description="FlowLens standalone MOCK contract harness")
    parser.add_argument("--track", choices=("A", "B"), required=True)
    parser.add_argument("--fixtures", type=Path, default=Path("contracts/examples"))
    args = parser.parse_args()
    track = cast(Literal["A", "B"], args.track)
    fixture: Path = args.fixtures
    context = RequestContext.model_validate_json((fixture / "context.json").read_text())
    result = JobResult.model_validate_json((fixture / "job_result.json").read_text())
    segment = TranscriptSegment.model_validate_json((fixture / "transcript.json").read_text())
    events = [
        SourceEvent.model_validate_json(json.dumps(row))
        for row in json.loads((fixture / "events.json").read_text())
    ]
    with TemporaryDirectory(prefix="flowlens-contract-") as temp:
        bundle = build_harness(track, db_path=Path(temp) / "repositories.db")
        reader = FakePlatform(events, [segment])
        if len(reader.read_events(context)) != 1:
            raise RuntimeError("as-known fixture mismatch")
        validated = bundle.analysis.validate(context, result, reader)
        db = SQLiteHarness(Path(temp) / "disposable.db")
        db.seed_job(validated)
        first = db.accept(validated, now_ms=100)
        if db.accept(validated, now_ms=100) != first:
            raise RuntimeError("duplicate commit receipt mismatch")
        if bundle.transactions is None:
            raise RuntimeError("transaction harness missing")
        with bundle.transactions.begin() as uow:
            bundle.analysis.accept(context, validated, uow)
            uow.commit()
    print(
        json.dumps(
            {
                "profile": "MOCK",
                "track": track,
                "contract_version": "1.0.0",
                "provider_calls": 0,
                "status": "passed",
                "database": "disposable-cleaned",
            }
        )
    )


if __name__ == "__main__":
    main()
