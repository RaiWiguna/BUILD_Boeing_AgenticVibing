// Copy guard (G-01/G-02/G-06): user-facing source must not offer clearance execution,
// LIVE operation, or claim a runway is safe/clear from absence of findings.
// Synthetic transcript seed data is source content (radio phraseology) and is excluded.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src');
const RULES = [
  { re: /\b(execute|send)\s+(clearance|command|instruction)/i, why: 'no clearance/command execution path' },
  { re: />\s*(Execute|Apply option|Send)\s*</, why: 'no execute/send controls on options' },
  { re: /['">]\s*LIVE\s*['"<]/, why: 'no LIVE indicator in an offline replay product' },
  { re: /runway (is )?(safe|clear)\b(?![^'"`]*(does not|not a|isn't|is not))/i, why: 'never claim runway safe/clear' },
  { re: /connect (radio|vhf|microphone)/i, why: 'no live feed connection' },
];
const ALLOW = [/does not mean the runway is clear/i, /does not indicate whether the runway is clear/i];

const files = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(tsx?|css)$/.test(name) && !p.includes(`${path.sep}generated${path.sep}`) && !p.includes(`${path.sep}seed${path.sep}`)) files.push(p);
  }
})(root);

let failures = 0;
for (const file of files) {
  readFileSync(file, 'utf8').split('\n').forEach((line, i) => {
    if (line.trim().startsWith('//') || line.trim().startsWith('*')) return;
    for (const rule of RULES) {
      if (rule.re.test(line) && !ALLOW.some((a) => a.test(line))) {
        failures += 1;
        console.error(`${path.relative(process.cwd(), file)}:${i + 1}  ${rule.why}\n    ${line.trim().slice(0, 160)}`);
      }
    }
  });
}
if (failures) {
  console.error(`\n${failures} copy-guard violation(s).`);
  process.exit(1);
}
console.log(`Copy guard passed (${files.length} files).`);
