import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { DemoScenarioChoice, DemoScenarios } from '@/api/demo';
import { demoPort } from '@/api/adapters/demo';
import { renderApp } from './harness';

const recording = (part: string, position: 'main' | 'before' = 'main') => [
  { name: `${part}.wav`, role: 'audio' as const, position, part },
  { name: `${part}.csv`, role: 'adsb' as const, position, part },
];
const cases: DemoScenarioChoice[] = [
  { id: '88', title: 'Original', files: [...recording('87', 'before'), ...recording('88')] },
  ...['50', '51', '47', '156', '123'].map((id) => ({ id, title: `Case ${id}`, files: [...(id === '51' ? recording('50', 'before') : []), ...recording(id)], limits: { before: 1, after: 1 } })),
];
const catalogue: DemoScenarios = { scenarios: cases, files: cases.flatMap((c) => c.files), expected_files: [] };
const file = (name: string) => new File(['fixture'], name);
const mainInput = (role: 'audio' | 'adsb') => within(screen.getByRole('region', { name: 'Main recording' })).getByText(role === 'audio' ? 'Radio audio' : 'ADS-B').closest('div.flex')!.querySelector<HTMLInputElement>('input[type=file]')!;

beforeEach(() => {
  vi.spyOn(demoPort, 'health').mockResolvedValue({ status: 'alive', profile: 'demo', database: true, scenarios: 6, version: 'test' });
  vi.spyOn(demoPort, 'scenarios').mockResolvedValue(catalogue);
  vi.spyOn(demoPort, 'listWorkspaces').mockResolvedValue([]);
});
afterEach(() => vi.restoreAllMocks());

describe('import case recognition through the real form', () => {
  it.each(['50', '51', '47', '156', '123'])('recognises %s through Choose without selecting a case first', async (part) => {
    const user = userEvent.setup();
    const upload = vi.spyOn(demoPort, 'createWorkspace').mockRejectedValue(new Error('Test stops before processing'));
    await renderApp('/sessions/import');
    expect(await screen.findByRole('combobox', { name: 'Case' })).toHaveValue('88');
    await user.type(screen.getByRole('textbox', { name: 'Session name' }), `New ${part}`);
    await user.upload(mainInput('audio'), file(`${part}.wav`));
    expect(screen.getByRole('combobox', { name: 'Case' })).toHaveValue(part);
    expect(screen.queryByText('Not a recording of this scenario')).toBeNull();
    expect(screen.getByRole('button', { name: 'Upload and process' })).toBeDisabled();
    await user.upload(mainInput('adsb'), file(`${part}.csv`));
    await user.click(screen.getByRole('button', { name: 'Upload and process' }));
    await waitFor(() => expect(upload).toHaveBeenCalledOnce());
    expect(upload.mock.calls[0]?.[4]).toBe(part);
    expect(upload.mock.calls[0]?.[1].map((f) => [f.file.name, f.position])).toEqual([[`${part}.wav`, 'main'], [`${part}.csv`, 'main']]);
  });

  it('recognises CSV-first and files chosen before the catalogue arrives', async () => {
    let deliver!: (c: DemoScenarios) => void;
    vi.mocked(demoPort.scenarios).mockReturnValue(new Promise((resolve) => { deliver = resolve; }));
    const user = userEvent.setup();
    await renderApp('/sessions/import');
    await screen.findByRole('textbox', { name: 'Session name' });
    await waitFor(() => expect(deliver).toBeTypeOf('function'));
    await user.upload(mainInput('adsb'), file('50.csv'));
    deliver(catalogue);
    expect(await screen.findByRole('combobox', { name: 'Case' })).toHaveValue('50');
    await user.upload(mainInput('audio'), file('50.wav'));
    expect(screen.queryByText('Not a recording of this scenario')).toBeNull();
  });

  it('infers 51 from a batch with 50 before, regardless of file order', async () => {
    const user = userEvent.setup();
    const { container } = await renderApp('/sessions/import');
    await screen.findByRole('combobox', { name: 'Case' });
    await user.upload(container.querySelector<HTMLInputElement>('input[multiple]')!, ['50.wav', '51.csv', '51.wav', '50.csv'].map(file));
    expect(screen.getByRole('combobox', { name: 'Case' })).toHaveValue('51');
    expect(within(screen.getByRole('region', { name: 'Before' })).getByText('50.wav')).toBeInTheDocument();
    expect(within(screen.getByRole('region', { name: 'Main recording' })).getByText('51.wav')).toBeInTheDocument();
  });

  it('preserves an explicit 51 choice when 50 is added as before', async () => {
    const user = userEvent.setup();
    const { container } = await renderApp('/sessions/import');
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Case' }), '51');
    await user.upload(container.querySelector<HTMLInputElement>('input[multiple]')!, file('50.wav'));
    expect(screen.getByRole('combobox', { name: 'Case' })).toHaveValue('51');
    expect(within(screen.getByRole('region', { name: 'Before' })).getByText('50.wav')).toBeInTheDocument();
    await user.upload(mainInput('audio'), file('51.wav'));
    expect(screen.queryByText('Not a recording of this scenario')).toBeNull();
  });

  it('rejects a different main through Choose instead of overwriting its selected case', async () => {
    const user = userEvent.setup();
    await renderApp('/sessions/import');
    await screen.findByRole('combobox', { name: 'Case' });
    await user.upload(mainInput('audio'), file('50.wav'));
    await user.upload(mainInput('adsb'), file('123.csv'));
    expect(screen.getByRole('combobox', { name: 'Case' })).toHaveValue('50');
    expect(screen.getByText(/Not added: 123.csv/)).toBeInTheDocument();
    expect(screen.getByText('50.wav')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upload and process' })).toBeDisabled();
  });
});
