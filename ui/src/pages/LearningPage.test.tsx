// @vitest-environment jsdom
import {cleanup, render, screen} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import {api} from '../api';
import type {LearningSummary} from '../learning';
import type {RunSummary} from '../types';
import LearningPage from './LearningPage';

vi.mock('../api',()=>({api:{getRun:vi.fn(),learning:{summary:vi.fn(),exportUrl:vi.fn(),observationsUrl:vi.fn()}}}));
vi.mock('../lib/reviewer',()=>({useReviewer:()=>({session:{is_admin:false},name:'reviewer@bd.com'})}));
const summary=():LearningSummary=>({enabled:true,collection_mode:'automatic',setup_issue:null,review_events:3,groups:[],labels:[],counts:{annotated:0,pending:0,verified_train:0,verified_evaluation:0},tasks:[],latest_evaluation:null});
const show=()=>render(<MemoryRouter initialEntries={['/runs/run/learning']}><Routes><Route path='/runs/:runId/learning' element={<LearningPage/>}/></Routes></MemoryRouter>);
beforeEach(()=>{vi.clearAllMocks();vi.mocked(api.getRun).mockResolvedValue({permission:'owner'} as RunSummary);vi.mocked(api.learning.summary).mockResolvedValue(summary());});
afterEach(cleanup);

it('shows automatic collection without an Enable action',async()=>{
 show();
 expect(await screen.findByText('Review data is collected automatically')).toBeTruthy();
 expect(screen.queryByRole('button',{name:/Enable/})).toBeNull();
 expect(screen.getByText('Recorded review events')).toBeTruthy();
 expect(screen.getByText(/independent verification before they become learning examples/)).toBeTruthy();
});

it('explains setup issues while confirming review history collection continues',async()=>{
 vi.mocked(api.learning.summary).mockResolvedValue({...summary(),enabled:false,setup_issue:'Resolve the product identities before verified learning can start.'});
 show();
 expect(await screen.findByText('Verified learning needs attention')).toBeTruthy();
 expect(screen.getByText('Resolve the product identities before verified learning can start.')).toBeTruthy();
 expect(screen.getByRole('link',{name:'Inspect documents'}).getAttribute('href')).toBe('/runs/run/documents');
 expect(screen.queryByRole('button',{name:/Enable/})).toBeNull();
});

it('shows automatic status to viewers without offering protected exports or rebuilding',async()=>{
 vi.mocked(api.getRun).mockResolvedValue({permission:'view'} as RunSummary);show();
 expect(await screen.findByText('Review data is collected automatically')).toBeTruthy();
 expect(screen.queryByRole('button',{name:'Rebuild and evaluate'})).toBeNull();
 expect(screen.queryByRole('link',{name:'Training dataset'})).toBeNull();
});
