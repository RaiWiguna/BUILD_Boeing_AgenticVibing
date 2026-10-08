import { describe, expect, it } from 'vitest';
import { formatAge, formatOffset, parseOffset } from '@/lib/time';

describe('replay time helpers', () => {
  it('formats session offsets with tenths', () => {
    expect(formatOffset(322_000)).toBe('05:22.0');
    expect(formatOffset(1_120_000, { tenths: false })).toBe('18:40');
    expect(formatOffset(-5)).toBe('00:00.0');
  });

  it('parses user-entered offsets and rejects invalid input', () => {
    expect(parseOffset('05:22.0')).toBe(322_000);
    expect(parseOffset('5:22')).toBe(322_000);
    expect(parseOffset('1:00:01')).toBe(3_601_000);
    expect(parseOffset('12')).toBe(12_000);
    expect(parseOffset('05:75')).toBeNull();
    expect(parseOffset('abc')).toBeNull();
  });

  it('describes source age without inventing precision', () => {
    expect(formatAge(null)).toBe('—');
    expect(formatAge(2_000)).toBe('2 s ago');
    expect(formatAge(120_000)).toBe('2 min ago');
  });
});
