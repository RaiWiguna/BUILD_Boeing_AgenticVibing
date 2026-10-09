"""PRD capacity ceilings apply before a source can be committed."""

from uuid import uuid4

import pytest
from flowlens.imports.staging import FilePreview, ImportFailure, ImportLimits
from test_imports import importer as importer


def test_prd_upload_byte_defaults():
    limits = ImportLimits()
    assert limits.max_file_bytes == 512 * 1024**2
    assert limits.max_total_bytes == 2 * 1024**3


@pytest.mark.parametrize("channels,durations", [(2, [3600001]), (1, [3600000, 3600001])])
def test_total_channel_minutes_bounded_before_preview(importer, channels, durations):
    service, auth, _ = importer
    with pytest.raises(ImportFailure) as error:
        session = service.start(auth.token.get_secret_value(), "over-duration")
        try:
            for index, duration in enumerate(durations):
                sink = session.add("audio", f"channel{index}.wav", "audio/wav")
                facts = FilePreview(
                    id=uuid4(),
                    role="audio",
                    filename=f"channel{index}.wav",
                    media_type="audio/wav",
                    profile="wav",
                    sha256="a" * 64,
                    size_bytes=44,
                    channels=channels,
                    sample_rate_hz=16000,
                    frames=duration * 16,
                    duration_ms=duration,
                )
                # Decoder facts are controlled here; full decoding is measured separately.
                sink.inspect = lambda facts=facts: facts
            session.finish()
        finally:
            session.abort()
    assert error.value.issues[0].code == "TOTAL_DURATION_LIMIT"
    assert not list(service.root.rglob("*.upload"))
