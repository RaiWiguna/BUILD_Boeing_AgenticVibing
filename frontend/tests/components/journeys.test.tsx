import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import { F03, renderApp, S1 } from './harness';

const AXE = { rules: { 'color-contrast': { enabled: false }, region: { enabled: false } } };

describe('MOCK UI journeys (component level)', () => {
  it('finding review starts empty, requires a reason and appends a revision', async () => {
    const user = userEvent.setup();
    const { container } = await renderApp(`/s/${S1}/review/findings?mode=debrief&t=322000&finding=${F03}`);
    await screen.findByRole('heading', { name: 'Reviewer decision' }, { timeout: 4000 });

    const decision = () => within(screen.getByRole('radiogroup', { name: 'Decision' }));
    expect(decision().getAllByRole('radio')).toHaveLength(3);
    decision().getAllByRole('radio').forEach((r) => expect(r).not.toBeChecked());
    const save = screen.getByRole('button', { name: 'Save review' });
    expect(save).toHaveAttribute('aria-disabled', 'true');

    await user.click(decision().getByRole('radio', { name: 'Cannot be determined yet' }));
    await user.click(save);
    expect(await screen.findByText(/A reason is required/)).toBeInTheDocument();

    await user.type(screen.getByRole('textbox', { name: /Reason/ }), 'Speaker identity not confirmed in audio.');
    await user.click(screen.getByRole('button', { name: 'Save review' }));
    expect(await screen.findByText(/Revision 1 · You/)).toBeInTheDocument();
    // Form resets to no selection after an append-only save.
    await waitFor(() => decision().getAllByRole('radio').forEach((r) => expect(r).not.toBeChecked()));

    expect(await axe(container, AXE)).toHaveNoViolations();
  });

  it('debrief labels AI interpretation, locks provenance and keeps audio export off', async () => {
    const user = userEvent.setup();
    const { container } = await renderApp(`/s/${S1}/debrief`);
    expect(await screen.findByText('Key item to review', undefined, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByText(/AI interpretation · Mock/i)).toBeInTheDocument();
    expect(screen.getAllByText('SYNTHETIC').length).toBeGreaterThan(0);

    // Export options live in a sheet opened from the header (decision D-4).
    await user.click(screen.getByRole('button', { name: 'Export report' }));
    const provenance = await screen.findByRole('switch', { name: /Include provenance/ });
    expect(provenance).toBeChecked();
    expect(provenance).toBeDisabled();
    const audio = screen.getByRole('switch', { name: /Include audio/ });
    expect(audio).not.toBeChecked();
    expect(audio).toBeDisabled();

    expect(await axe(container, AXE)).toHaveNoViolations();
    expect(await axe(screen.getByRole('dialog', { name: 'Export report' }), AXE)).toHaveNoViolations();
  });

  it('unknown answers say so and carry no evidence', async () => {
    const user = userEvent.setup();
    await renderApp(`/s/${S1}/ask?t=322000`);
    const box = await screen.findByRole('textbox', { name: 'Question' }, { timeout: 4000 });
    await user.type(box, 'Is runway 27 clear for departure?{Enter}');
    const answer = await screen.findByRole('article', { name: /Is runway 27 clear/ });
    expect(within(answer).getByText(/Unknown · not covered/)).toBeInTheDocument();
    expect(within(answer).queryByRole('button', { name: /Open evidence/ })).toBeNull();
  });

  it('restricted admin sections do not load for non-admins', async () => {
    await renderApp('/settings/users');
    expect(await screen.findByText('Access restricted', undefined, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.queryByRole('table')).toBeNull();
  });
});
