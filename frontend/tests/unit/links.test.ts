import { describe, expect, it } from 'vitest';
import { areaFromPath, lensAreaOf, parseLens, scopeFromParams, sessionHref } from '@/lib/links';

describe('sessionHref', () => {
  it('keeps run, lens and t and adds focus params', () => {
    expect(sessionHref('review/findings', { sid: 's1', run: 'r3', lens: 'as-known', t: 320000.4, focus: { finding: 'f1' } })).toBe('/s/s1/review/findings?run=r3&mode=as-known&t=320000&finding=f1');
  });
  it('omits empty values', () => {
    expect(sessionHref('workspace', { sid: 's1', run: null, lens: null, t: null, focus: { finding: undefined } })).toBe('/s/s1/workspace');
  });
  it('keeps t = 0', () => {
    expect(sessionHref('workspace', { sid: 's1', t: 0 })).toBe('/s/s1/workspace?t=0');
  });
});

describe('lensAreaOf', () => {
  it('treats review, debrief, metrics and ask as full-session analysis', () => {
    for (const a of ['review/findings', 'review/transcript', 'debrief', 'metrics', 'ask']) expect(lensAreaOf(`/s/x/${a}`)).toBe('analysis');
  });
  it('treats workspace and memory as replay', () => {
    expect(lensAreaOf('/s/x/workspace')).toBe('replay');
    expect(lensAreaOf('/s/x/memory/abc')).toBe('replay');
    expect(lensAreaOf('/sessions')).toBe('replay');
  });
});

describe('areaFromPath', () => {
  it('collapses object memory pages but keeps runway memory', () => {
    expect(areaFromPath('/s/x/memory/abc')).toBe('memory');
    expect(areaFromPath('/s/x/memory/runway')).toBe('memory/runway');
    expect(areaFromPath('/s/x/review/options')).toBe('review/options');
    expect(areaFromPath('/sessions')).toBe('workspace');
  });
});

describe('scopeFromParams', () => {
  it('reads run, a valid lens and a numeric t only', () => {
    expect(scopeFromParams(new URLSearchParams('run=r1&mode=debrief&t=5000&finding=f1'))).toEqual({ run: 'r1', lens: 'debrief', t: 5000 });
    expect(scopeFromParams(new URLSearchParams('mode=live&t=abc'))).toEqual({ run: null, lens: null, t: null });
    expect(parseLens('as-known')).toBe('as-known');
  });
});
