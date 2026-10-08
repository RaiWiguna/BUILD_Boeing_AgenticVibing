/** Deterministic identifiers for MOCK seed data (stable across reloads). */

function fnv(input: string, seed: number) {
  let h = seed >>> 0;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, '0');
}

function hex(input: string, length: number) {
  let out = '';
  let seed = 0x811c9dc5;
  while (out.length < length) {
    out += fnv(`${input}:${out.length}`, seed);
    seed = (seed + 0x9e3779b9) >>> 0;
  }
  return out.slice(0, length);
}

/** RFC 4122-shaped v4 UUID derived from a key. */
export function mid(key: string) {
  const h = hex(key, 32);
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-4${h.slice(13, 16)}-8${h.slice(17, 20)}-${h.slice(20, 32)}`;
}

export function sha(key: string) {
  return hex(`sha:${key}`, 64);
}

/** Deterministic pseudo-random in [0, 1). */
export function rand(key: string) {
  return parseInt(fnv(key, 0x12345678), 16) / 0xffffffff;
}

/** "05:12" | "05:12.4" → ms */
export function at(clock: string) {
  const [m, rest] = clock.split(':');
  const [s, t] = (rest ?? '0').split('.');
  return (Number(m) * 60 + Number(s)) * 1000 + Number(t ?? 0) * 100;
}
