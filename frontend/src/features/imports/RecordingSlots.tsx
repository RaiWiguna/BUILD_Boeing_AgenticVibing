/**
 * Recording lanes for import (DEMO track, ADR 0003): the main recording plus any number of
 * recordings before and after it, each with radio audio and an optional ADS-B file.
 * Files dropped anywhere are placed by their known position (paired by recording); a file
 * in the wrong lane is flagged with a one-click move. Recordings are added at import only.
 */
import { ArrowRightLeft, FileAudio, FileSpreadsheet, Plus, Trash2, TriangleAlert, Upload, X } from 'lucide-react';
import { useRef, useState, type DragEvent, type ReactNode } from 'react';
import type { DemoScenarios, FilePosition, FileRole, PlacedFile } from '@/api/demo';
import { Button } from '@/components/ui/button';
import { formatBytes } from '@/lib/time';
import { cn } from '@/lib/utils';

/** One recording: radio audio plus its optional ADS-B file. */
export type Group = { id: string } & Partial<Record<FileRole, File>>;
export type Side = 'before' | 'after';
export type Slots = { before: Group[]; main: Group; after: Group[] };

let nextId = 0;
const group = (): Group => ({ id: `g${++nextId}` });

export const EMPTY_SLOTS: Slots = { before: [], main: { id: 'main' }, after: [] };
const ROLES: FileRole[] = ['audio', 'adsb'];

export const roleOf = (name: string): FileRole | null => (/\.wav$/i.test(name) ? 'audio' : /\.csv$/i.test(name) ? 'adsb' : null);

const SIDE: Record<Side, { title: string; add: string; more: string }> = {
  before: { title: 'Before', add: 'Add recording before', more: 'Add another recording before' },
  after: { title: 'After', add: 'Add recording after', more: 'Add another recording after' },
};

const TILE: Record<FileRole, { label: string; accept: string; icon: typeof FileAudio; hint: string }> = {
  audio: { label: 'Radio audio', accept: '.wav', icon: FileAudio, hint: '.wav' },
  adsb: { label: 'ADS-B', accept: '.csv', icon: FileSpreadsheet, hint: '.csv · optional' },
};

const groupsOf = (slots: Slots, pos: FilePosition): Group[] => (pos === 'main' ? [slots.main] : slots[pos]);
const filled = (g: Group) => !!(g.audio || g.adsb);

function clone(slots: Slots): Slots {
  return { before: slots.before.map((g) => ({ ...g })), main: { ...slots.main }, after: slots.after.map((g) => ({ ...g })) };
}

export function placedFiles(slots: Slots): PlacedFile[] {
  return (['before', 'main', 'after'] as FilePosition[]).flatMap((position) => groupsOf(slots, position).flatMap((g) => ROLES.flatMap((role) => (g[role] ? [{ file: g[role]!, position }] : []))));
}

/** Put one file into a lane: next to its known partner file, else the first recording missing that role, else a new one. */
function put(next: Slots, pos: FilePosition, role: FileRole, f: File, known: DemoScenarios | undefined) {
  if (pos === 'main') return void (next.main[role] = f);
  const partOf = (file?: File) => (file ? known?.files.find((k) => k.name === file.name)?.part : undefined);
  const part = partOf(f);
  const lane = next[pos];
  const target =
    (part && lane.find((g) => ROLES.some((r) => partOf(g[r]) === part))) ??
    lane.find((g) => !g[role] && !ROLES.some((r) => { const p = partOf(g[r]); return p && part && p !== part; }));
  if (target) target[role] = f;
  else lane.push({ ...group(), [role]: f });
}

/**
 * Put files into lanes: a known file goes to its recorded position, others to `fallback`.
 * Known files are placed first so an unknown one never takes their slot; an unknown file
 * never replaces a file already in the main recording (it becomes a recording after it).
 */
export function place(slots: Slots, files: File[], known: DemoScenarios | undefined, fallback: FilePosition) {
  const next = clone(slots);
  const rejected: string[] = [];
  const positionOf = (f: File) => known?.files.find((k) => k.name === f.name)?.position;
  for (const f of [...files].sort((a, b) => Number(!positionOf(a)) - Number(!positionOf(b)))) {
    const role = roleOf(f.name);
    if (!role) {
      rejected.push(f.name);
      continue;
    }
    if (known?.limits && !positionOf(f)) { rejected.push(f.name); continue; }
    const pos = positionOf(f) ?? (fallback === 'main' && next.main[role] ? 'after' : fallback);
    if (known?.limits && pos === 'main' && next.main[role] && next.main[role]!.name !== f.name) {
      rejected.push(f.name); continue;
    }
    if (known?.limits && pos !== 'main' && next[pos].length >= known.limits[pos] && !next[pos].some((g) => !g[role])) {
      rejected.push(f.name); continue;
    }
    put(next, pos, role, f, known);
  }
  return { slots: next, rejected };
}

type Issue = { tone: 'notice' | 'discrepancy'; text: string; move?: FilePosition };
type IssueKey = `${string}:${FileRole}`;

export function issuesOf(slots: Slots, known: DemoScenarios | undefined) {
  const out: Partial<Record<IssueKey, Issue>> = {};
  const main = known?.files.find((k) => k.position === 'main' && k.role === 'audio')?.name ?? 'the main recording';
  for (const pos of ['before', 'main', 'after'] as FilePosition[]) {
    if (known?.limits && pos !== 'main' && slots[pos].filter(filled).length > known.limits[pos]) {
      const g = slots[pos][known.limits[pos]];
      if (g) out[`${g.id}:audio`] = { tone: 'discrepancy', text: `Only one ${pos} recording is supported` };
    }
    for (const g of groupsOf(slots, pos)) {
      for (const role of ROLES) {
        const f = g[role];
        if (!f) continue;
        const k = known?.files.find((x) => x.name === f.name);
        if (known && !k) out[`${g.id}:${role}`] = { tone: 'discrepancy', text: 'Not a recording of this scenario' };
        else if (k && k.position !== pos) out[`${g.id}:${role}`] = { tone: 'discrepancy', text: k.position === 'main' ? 'This is the main recording' : `Recorded ${k.position} ${main}`, move: k.position };
      }
      if (g.adsb && !g.audio) out[`${g.id}:audio`] = { tone: 'notice', text: 'Needed for the ADS-B file' };
    }
  }
  return out;
}

export function slotsReady(slots: Slots, known: DemoScenarios | undefined) {
  const issues = issuesOf(slots, known);
  return !!slots.main.audio && !!slots.main.adsb && Object.values(issues).every((i) => !i);
}

export function RecordingSlots({
  slots,
  onChange,
  known,
  disabled,
}: {
  slots: Slots;
  onChange: (slots: Slots, rejected: string[]) => void;
  known: DemoScenarios | undefined;
  disabled?: boolean;
}) {
  const issues = issuesOf(slots, known);
  const edit = (fn: (next: Slots) => void) => {
    const next = clone(slots);
    fn(next);
    onChange(next, []);
  };
  const find = (next: Slots, id: string) => [next.main, ...next.before, ...next.after].find((g) => g.id === id)!;
  const setFile = (id: string, role: FileRole, file: File | undefined) => edit((next) => void (find(next, id)[role] = file));
  const move = (id: string, role: FileRole, to: FilePosition) =>
    edit((next) => {
      const g = find(next, id);
      const f = g[role]!;
      g[role] = undefined;
      put(next, to, role, f, known);
      for (const s of ['before', 'after'] as Side[]) next[s] = next[s].filter((x) => filled(x) || x.id !== id);
    });
  const drop = (pos: FilePosition, files: File[]) => {
    const r = place(slots, files, known, pos);
    onChange(r.slots, r.rejected);
  };

  const tiles = (g: Group, pos: FilePosition) =>
    ROLES.map((role) => (
      <FileTile
        key={role}
        role={role}
        file={g[role] ?? null}
        issue={issues[`${g.id}:${role}`]}
        required={pos === 'main'}
        disabled={disabled}
        onPick={(file) => (roleOf(file.name) === role ? setFile(g.id, role, file) : drop(pos, [file]))}
        onRemove={() => setFile(g.id, role, undefined)}
        onMove={(to) => move(g.id, role, to)}
      />
    ));

  const side = (s: Side) => {
    const lane = slots[s];
    if (known?.limits && !known.files.some((f) => f.position === s)) return null;
    if (!lane.length)
      return (
        <AddButton disabled={disabled} onClick={() => edit((next) => void next[s].push(group()))}>
          {SIDE[s].add}
        </AddButton>
      );
    return (
      <Lane title={SIDE[s].title} count={lane.length} onDrop={(files) => drop(s, files)} disabled={disabled}>
        <ol className="space-y-2.5">
          {lane.map((g, i) => (
            <li key={g.id} className="rounded-[14px] border border-hairline-soft bg-surface/50 p-2.5">
              <div className="mb-2 flex items-center justify-between gap-2 px-0.5">
                <p className="text-[12.5px] font-medium text-ink-2">Recording {i + 1}</p>
                <Button variant="ghost" size="icon-sm" aria-label={`Remove ${SIDE[s].title.toLowerCase()} recording ${i + 1}`} disabled={disabled} onClick={() => edit((next) => void (next[s] = next[s].filter((x) => x.id !== g.id)))}>
                  <X />
                </Button>
              </div>
              <div className="grid gap-2.5 sm:grid-cols-2">{tiles(g, s)}</div>
            </li>
          ))}
        </ol>
        <AddButton compact disabled={disabled || !!(known?.limits && lane.length >= known.limits[s])} onClick={() => edit((next) => void next[s].push(group()))}>
          {SIDE[s].more}
        </AddButton>
      </Lane>
    );
  };

  return (
    <ol className="relative space-y-3" aria-label="Recordings">
      <li>{side('before')}</li>
      <li>
        <Lane title="Main recording" required onDrop={(files) => drop('main', files)} disabled={disabled}>
          <div className="grid gap-2.5 sm:grid-cols-2">{tiles(slots.main, 'main')}</div>
        </Lane>
      </li>
      <li>{side('after')}</li>
    </ol>
  );
}

function AddButton({ children, onClick, disabled, compact }: { children: ReactNode; onClick: () => void; disabled?: boolean; compact?: boolean }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2.5 rounded-[16px] border border-dashed border-hairline-strong text-left font-medium text-data transition-colors hover:border-data hover:bg-data-tint/40 disabled:opacity-60',
        compact ? 'mt-2.5 px-3 py-2 text-[13.5px]' : 'px-4 py-3 text-[14.5px]',
      )}
    >
      <span className={cn('inline-flex items-center justify-center rounded-full bg-data-tint text-data', compact ? 'size-5' : 'size-6')}>
        <Plus className={compact ? 'size-3.5' : 'size-4'} aria-hidden />
      </span>
      {children}
    </button>
  );
}

function Lane({ title, count, required, children, onDrop, disabled }: { title: string; count?: number; required?: boolean; children: ReactNode; onDrop: (files: File[]) => void; disabled?: boolean }) {
  const [over, setOver] = useState(false);
  return (
    <section
      aria-label={title}
      onDragOver={(e: DragEvent) => {
        e.preventDefault();
        if (!disabled) setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e: DragEvent) => {
        e.preventDefault();
        setOver(false);
        if (!disabled) onDrop(Array.from(e.dataTransfer.files));
      }}
      className={cn('rounded-[18px] border p-3.5 transition-colors', over ? 'border-data bg-data-tint/50' : required ? 'border-hairline bg-surface' : 'border-hairline bg-sunken/40')}
    >
      <div className="mb-2.5 flex items-center gap-2 px-0.5">
        <h3 className="text-[14px] font-semibold text-ink">{title}</h3>
        {count != null && <span className="text-[12.5px] tabular text-ink-3">{count === 1 ? '1 recording' : `${count} recordings`}</span>}
      </div>
      {children}
    </section>
  );
}

function FileTile({
  role,
  file,
  issue,
  required,
  disabled,
  onPick,
  onRemove,
  onMove,
}: {
  role: FileRole;
  file: File | null;
  issue?: Issue;
  required: boolean;
  disabled?: boolean;
  onPick: (f: File) => void;
  onRemove: () => void;
  onMove: (to: FilePosition) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const meta = TILE[role];
  const Icon = meta.icon;
  const name = file?.name;
  const bad = issue?.tone === 'discrepancy';
  return (
    <div className={cn('flex min-h-[68px] items-center gap-3 rounded-[14px] border px-3 py-2.5', name ? (bad ? 'border-discrepancy/40 bg-discrepancy-tint/40' : 'border-hairline bg-surface') : 'border-dashed border-hairline-strong bg-surface/60')}>
      <span className={cn('inline-flex size-9 shrink-0 items-center justify-center rounded-[10px]', name ? 'bg-data-tint text-data' : 'bg-track text-ink-3')}>
        <Icon aria-hidden className="size-[18px]" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[12.5px] font-medium text-ink-2">{meta.label}</p>
        {name ? (
          <>
            <p className="truncate text-[14.5px] text-ink" title={name}>
              {name}
            </p>
            <p className={cn('flex items-center gap-1 text-[12.5px]', issue ? (bad ? 'text-discrepancy' : 'text-notice') : 'text-ink-3')}>
              {issue && <TriangleAlert aria-hidden className="size-3.5 shrink-0" />}
              {issue ? issue.text : formatBytes(file!.size)}
            </p>
          </>
        ) : (
          <p className={cn('text-[12.5px]', issue ? 'text-notice' : 'text-ink-3')}>{issue ? issue.text : role === 'adsb' && required ? '.csv' : meta.hint}</p>
        )}
      </div>
      <input ref={input} type="file" accept={meta.accept} className="sr-only" tabIndex={-1} aria-hidden onChange={(e) => (e.target.files?.[0] && onPick(e.target.files[0]), (e.target.value = ''))} />
      {issue?.move && (
        <Button variant="secondary" size="xs" onClick={() => onMove(issue.move!)} disabled={disabled}>
          <ArrowRightLeft /> Move
        </Button>
      )}
      {file ? (
        <Button variant="ghost" size="icon-sm" aria-label={`Remove ${file.name}`} onClick={onRemove} disabled={disabled}>
          <Trash2 />
        </Button>
      ) : (
        <Button variant="ghost" size="sm" onClick={() => input.current?.click()} disabled={disabled} aria-label={`Choose ${meta.label} file`}>
          <Upload /> Choose
        </Button>
      )}
    </div>
  );
}
