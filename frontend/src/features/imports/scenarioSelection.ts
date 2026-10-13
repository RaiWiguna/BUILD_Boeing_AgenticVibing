import type { DemoScenarioChoice, DemoScenarios, FilePosition } from '@/api/demo';
import { placedFiles, roleOf, type Slots } from './RecordingSlots';

/** Infer an empty main from its files; an existing main or an explicit companion lane keeps its case. */
export function scenarioForFiles(catalogue: DemoScenarios | undefined, selected: DemoScenarioChoice | undefined, slots: Slots, files: File[], position: FilePosition) {
  if (!catalogue?.scenarios || slots.main.audio || position !== 'main') return selected;
  const names = [...placedFiles(slots).map((f) => f.file.name), ...files.filter((f) => roleOf(f.name)).map((f) => f.name)];
  if (!names.length) return selected;
  const accepts = (c: DemoScenarioChoice) => names.every((name) => c.files.some((f) => f.name === name));
  // In case 51, 50 remains before; don't reinterpret an already compatible choice.
  if (selected && accepts(selected)) return selected;
  const matches = catalogue.scenarios.filter((c) => accepts(c) && c.files.some((f) => f.position === 'main' && files.some((incoming) => incoming.name === f.name)));
  return matches.length === 1 ? matches[0] : selected;
}
