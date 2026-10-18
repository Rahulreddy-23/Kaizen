// @vitest-environment jsdom
import {act, cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import {api, type RunProgress} from '../api';
import type {RunSummary} from '../types';
import RunsPage from './RunsPage';

vi.mock('../api', () => ({api: {health: vi.fn(), listRuns: vi.fn(), listDeletedRuns: vi.fn(), uploadRun: vi.fn(), runFromPath: vi.fn(), loadDemo: vi.fn()}}));
vi.mock('../lib/reviewer', () => ({useReviewer: () => ({session: {is_admin: true}})}));
vi.mock('../lib/toast', () => ({useToast: () => vi.fn()}));
afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.health).mockResolvedValue({hosted: false} as Awaited<ReturnType<typeof api.health>>);
  vi.mocked(api.listRuns).mockResolvedValue([]);
});
const summary = {run_id: 'saved'} as RunSummary;
const show = async () => {
  render(<MemoryRouter><Routes><Route path='/' element={<RunsPage/>}/><Route path='/runs/:id' element={<h1>Saved run</h1>}/></Routes></MemoryRouter>);
  fireEvent.click(screen.getByRole('button', {name: 'New cross-check'}));
  await screen.findByText('Advanced: use a local folder path');
};
const choose = (prefix: string) => fireEvent.change(screen.getByLabelText('Individual documents'), {target: {files: ['bom.xlsx', 'label.pdf', 'drawing.pdf'].map(name => new File(['data'], `${prefix}-${name}`))}});

it('shows 0–100 progress beside Start cross-check and locks inputs until saving completes', async () => {
  let update!: (value: RunProgress) => void, finish!: (run: RunSummary) => void;
  vi.mocked(api.uploadRun).mockImplementation((_folders, _name, progress) => {update = progress!; return new Promise(resolve => {finish = resolve;});});
  await show(); choose('one');
  fireEvent.click(screen.getByRole('button', {name: 'Start cross-check'}));
  expect(screen.getByRole('progressbar').getAttribute('value')).toBe('0');
  expect(screen.getByRole('progressbar').closest('.run-start-action')?.querySelector('button')?.textContent).toContain('Start cross-check');
  expect((screen.getByLabelText(/Run name/) as HTMLInputElement).disabled).toBe(true);
  expect((screen.getByRole('button', {name: 'Close'}) as HTMLButtonElement).disabled).toBe(true);
  act(() => update({percent: 70, stage: 'Comparing documents'}));
  expect(screen.getByText('70%')).toBeTruthy();
  await act(async () => {finish(summary);});
  expect(screen.getByText('100%')).toBeTruthy();
  expect(await screen.findByRole('heading', {name: 'Saved run'})).toBeTruthy();
});

it('retains only failed upload sets and retries them without recreating the successes', async () => {
  vi.mocked(api.uploadRun).mockResolvedValueOnce(summary).mockRejectedValueOnce(new Error('Unreadable drawing')).mockResolvedValueOnce(summary);
  await show(); choose('one'); choose('two');
  fireEvent.click(screen.getByRole('button', {name: 'Create 2 runs'}));
  await screen.findByText(/Created 1 run · 1 folder could not be checked/);
  expect(screen.getAllByRole('button', {name: /Remove Selected files/})).toHaveLength(1);
  expect(screen.queryByRole('progressbar')).toBeNull();
  fireEvent.click(screen.getByRole('button', {name: 'Start cross-check'}));
  await screen.findByRole('heading', {name: 'Saved run'});
  expect(api.uploadRun).toHaveBeenCalledTimes(3);
  expect(vi.mocked(api.uploadRun).mock.calls[2][0][0].name).toBe('Selected files (2)');
});

it('shows local-path progress beside Run folder and reports partial successes', async () => {
  let finish!: (value: Awaited<ReturnType<typeof api.runFromPath>>) => void;
  vi.mocked(api.runFromPath).mockImplementation(() => new Promise(resolve => {finish = resolve;}));
  await show();
  fireEvent.click(screen.getByText('Advanced: use a local folder path'));
  fireEvent.change(screen.getByLabelText('Local folder path'), {target: {value: '/kits'}});
  fireEvent.click(screen.getByRole('button', {name: 'Run folder'}));
  expect(screen.getByRole('progressbar').closest('.run-start-action')?.querySelector('button')?.textContent).toContain('Run folder');
  await act(async () => finish({runs: [summary], failures: [{path: '/kits/bad', message: 'Unreadable label'}]}));
  await waitFor(() => expect((screen.getByLabelText('Local folder path') as HTMLInputElement).value).toBe('/kits/bad'));
  expect(screen.getByText(/Created 1 run · 1 folder could not be checked/)).toBeTruthy();
  expect(screen.queryByRole('progressbar')).toBeNull();
});
