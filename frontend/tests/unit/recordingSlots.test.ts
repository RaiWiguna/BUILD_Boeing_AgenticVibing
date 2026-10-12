import { describe, expect, it } from 'vitest';
import type { DemoScenarios } from '@/api/demo';
import { EMPTY_SLOTS, issuesOf, place, placedFiles, slotsReady } from '@/features/imports/RecordingSlots';

const known: DemoScenarios = {
  expected_files: [],
  files: [
    { name: '87.wav', role: 'audio', position: 'before', part: '87' },
    { name: 'kagc_adsb_2022-09-10_87.csv', role: 'adsb', position: 'before', part: '87' },
    { name: '88.wav', role: 'audio', position: 'main', part: '88' },
    { name: 'kagc_adsb_2022-09-10_88.csv', role: 'adsb', position: 'main', part: '88' },
  ],
};
const file = (name: string) => new File(['x'], name);

describe('recording slots', () => {
  it('places known files in their lanes and pairs a recording with its ADS-B file', () => {
    const { slots, rejected } = place(EMPTY_SLOTS, ['88.wav', 'kagc_adsb_2022-09-10_87.csv', 'kagc_adsb_2022-09-10_88.csv', '87.wav', 'notes.txt'].map(file), known, 'main');
    expect(rejected).toEqual(['notes.txt']);
    expect(slots.before).toHaveLength(1);
    expect(slots.before[0]!.audio?.name).toBe('87.wav');
    expect(slots.before[0]!.adsb?.name).toBe('kagc_adsb_2022-09-10_87.csv');
    expect(slots.main.audio?.name).toBe('88.wav');
    expect(slotsReady(slots, known)).toBe(true);
    expect(placedFiles(slots).map((p) => `${p.position}:${p.file.name}`)).toContain('before:87.wav');
  });

  it('never lets an unknown file take or replace the main recording', () => {
    const { slots } = place(EMPTY_SLOTS, ['86.wav', '88.wav', 'kagc_adsb_2022-09-10_88.csv'].map(file), known, 'main');
    expect(slots.main.audio?.name).toBe('88.wav');
    expect(slots.after.map((g) => g.audio?.name)).toEqual(['86.wav']);
  });

  it('holds several recordings before and after; unknown ones are flagged', () => {
    let { slots } = place(EMPTY_SLOTS, ['88.wav', 'kagc_adsb_2022-09-10_88.csv', '87.wav'].map(file), known, 'main');
    slots = place(slots, [file('86.wav'), file('85.wav')], known, 'before').slots;
    slots = place(slots, [file('89.wav')], known, 'after').slots;
    expect(slots.before.map((g) => g.audio?.name)).toEqual(['87.wav', '86.wav', '85.wav']);
    expect(slots.after.map((g) => g.audio?.name)).toEqual(['89.wav']);
    const issues = issuesOf(slots, known);
    expect(Object.values(issues).filter(Boolean)).toHaveLength(3);
    expect(slotsReady(slots, known)).toBe(false);
  });
});
