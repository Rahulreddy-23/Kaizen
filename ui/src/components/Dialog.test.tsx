// @vitest-environment jsdom
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {Dialog} from './ui';

afterEach(() => {cleanup(); vi.restoreAllMocks();});

it('blocks the close button, escape and backdrop while a save is in progress', () => {
  const close = vi.fn();
  const view = render(<Dialog open closeDisabled title="Upload" onClose={close}/>);
  expect((screen.getByRole('button', {name: 'Close'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.keyDown(document, {key: 'Escape'});
  fireEvent.mouseDown(screen.getByRole('dialog').parentElement!);
  expect(close).not.toHaveBeenCalled();
  view.rerender(<Dialog open title="Upload" onClose={close}/>);
  fireEvent.keyDown(document, {key: 'Escape'});
  expect(close).toHaveBeenCalledTimes(1);
});

it('keeps expandable filenames keyboard accessible when upload buttons are disabled', () => {
  vi.spyOn(HTMLElement.prototype, 'getClientRects').mockReturnValue([{}] as unknown as DOMRectList);
  render(<Dialog open closeDisabled title="Upload" onClose={() => {}} footer={<button disabled>Saving</button>}><details><summary>First folder</summary>Files</details><details><summary>Second folder</summary>Files</details></Dialog>);
  fireEvent.keyDown(document, {key: 'Tab'});
  expect(document.activeElement).toBe(screen.getByText('First folder'));
  fireEvent.keyDown(document, {key: 'Tab', shiftKey: true});
  expect(document.activeElement).toBe(screen.getByText('Second folder'));
});
