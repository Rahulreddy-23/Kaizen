// @vitest-environment jsdom
import {cleanup, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import {api} from '../api';
import EvidencePage from './EvidencePage';

vi.mock('../api', () => ({api:{getRow:vi.fn(),getResults:vi.fn()}}));
vi.mock('../lib/reviewer', () => ({useReviewer:() => ({viewerParams:{viewer:1,blind:false}})}));
vi.mock('../components/DecisionPanel', () => ({DecisionPanel:() => null}));
vi.mock('../components/EvidenceCard', () => ({EvidenceCard:() => null}));
vi.mock('../components/RowActions', () => ({SaveRelationshipPanel:() => null, ActionItemPanel:() => null}));
vi.mock('../components/GroundTruthPanel', () => ({GroundTruthPanel:() => null}));
afterEach(cleanup);

it.each(['exempt','item'])('distinguishes a %s row from a verified exact match', async role => {
  vi.mocked(api.getResults).mockResolvedValue({total:0,rows:[]} as never);
  vi.mocked(api.getRow).mockResolvedValue({result:{row_id:'row',sku:'700KIT',check:'BOM_DRAWING',role,classification:'EXACT',requires_validation:false,source_a:{id:'a'},source_b:role==='exempt'?null:{id:'b'},discrepancies:[],match_level:'NONE',score:0,explanation:'Packaging film has no required drawing callout.'},effective_classification:'EXACT',evidence:{a:null,b:null},permission:'view'} as never);
  render(<MemoryRouter initialEntries={['/runs/run/rows/row']}><Routes><Route path='/runs/:runId/rows/:rowId' element={<EvidencePage />} /></Routes></MemoryRouter>);
  if (role === 'exempt') {
    await screen.findByText('Not required by this check');
    expect(screen.queryByText('Exact')).toBeNull();
    expect(screen.queryByText('Auto-cleared')).toBeNull();
    expect(screen.queryByText('No discrepancy found.')).toBeNull();
    expect(screen.getByText(/No counterpart was verified/)).toBeTruthy();
  } else {
    await screen.findByText('Auto-cleared');
    expect(screen.getByText('Exact')).toBeTruthy();
    expect(screen.queryByText(/No counterpart was verified/)).toBeNull();
  }
});
