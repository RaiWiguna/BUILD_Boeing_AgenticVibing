"""Pure sample-based planning. Gaps are source-relative, half-open frame intervals."""

from fractions import Fraction

from flowlens.audio.models import AudioLimits, ChunkPlan, FrameRange
from flowlens.contracts.models import ClockMapping


def plan_chunks(
    *,
    decoded_frames: int,
    source_rate: int,
    channels: int,
    clock: ClockMapping,
    limits: AudioLimits,
    source_gaps: tuple[FrameRange, ...] = (),
) -> tuple[ChunkPlan, ...]:
    limits = AudioLimits.model_validate_json(limits.model_dump_json())
    clock = ClockMapping.model_validate_json(clock.model_dump_json())
    if (
        type(decoded_frames) is not int
        or decoded_frames <= 0
        or type(source_rate) is not int
        or type(channels) is not int
        or not 8000 <= source_rate <= limits.max_input_rate
        or not 1 <= channels <= limits.max_channels
        or decoded_frames > limits.max_duration_seconds * limits.output_rate
    ):
        raise ValueError("Invalid audio dimensions.")
    rate = limits.output_rate
    # Conservative rounding excludes any sample intersecting missing coverage.
    gaps: list[tuple[int, int]] = []
    last_source_end = 0
    for gap in source_gaps:
        FrameRange.model_validate_json(gap.model_dump_json())
        if gap.start < last_source_end or gap.end * rate > decoded_frames * source_rate:
            raise ValueError("Invalid source coverage.")
        start = gap.start * rate // source_rate
        end = (gap.end * rate + source_rate - 1) // source_rate
        if gaps and start <= gaps[-1][1]:
            gaps[-1] = (gaps[-1][0], max(end, gaps[-1][1]))
        else:
            gaps.append((start, end))
        last_source_end = gap.end
    spans: list[tuple[int, int, int]] = []
    cursor = 0
    missing = 0
    for start, end in gaps:
        if cursor < start:
            spans.append((cursor, start, missing))
        missing = end - start
        cursor = end
    if cursor < decoded_frames:
        spans.append((cursor, decoded_frames, missing))
    capacity = min(limits.chunk_ms * rate // 1000, (limits.max_chunk_bytes - 44) // 2)
    overlap = limits.overlap_ms * rate // 1000
    result: list[ChunkPlan] = []
    total_bytes = decoded_frames * channels * 2
    if total_bytes > limits.max_output_bytes:
        raise ValueError("Audio preparation limit exceeded.")
    for channel in range(channels):
        for segment, (start, stop, gap_before) in enumerate(spans):
            cursor = start
            previous_end = start
            while cursor < stop:
                end = min(stop, cursor + capacity)
                size = 44 + (end - cursor) * 2
                total_bytes += size
                if len(result) >= limits.max_chunks or total_bytes > limits.max_output_bytes:
                    raise ValueError("Audio preparation limit exceeded.")
                begin_ms = float(Fraction(cursor * 1000, rate))
                end_ms = float(Fraction(end * 1000, rate))
                offset = clock.offset_ms
                result.append(
                    ChunkPlan(
                        channel=channel,
                        derivative_frames=FrameRange(start=cursor, end=end),
                        source_frames=FrameRange(
                            start=cursor * source_rate // rate,
                            end=(end * source_rate + rate - 1) // rate,
                        ),
                        source_start_ms=begin_ms,
                        source_end_ms=end_ms,
                        session_start_ms=None if offset is None else begin_ms + offset,
                        session_end_ms=None if offset is None else end_ms + offset,
                        overlap_frames=max(0, previous_end - cursor),
                        coverage_segment=segment,
                        gap_before_source_frames=(
                            (gap_before * source_rate + rate - 1) // rate if cursor == start else 0
                        ),
                        expected_bytes=size,
                    )
                )
                previous_end = end
                if end == stop:
                    break
                cursor = end - overlap
    return tuple(result)
