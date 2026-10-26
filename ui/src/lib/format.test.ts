import {afterEach, describe, expect, it, vi} from "vitest";
import {fmtDayMonthYear} from "./format";

afterEach(()=>vi.unstubAllEnvs());

describe('marked document UTC dates',()=>{
  it.each(['Asia/Kolkata','America/Los_Angeles','UTC'])('matches PDF dates in %s',timezone=>{
    vi.stubEnv('TZ',timezone);
    expect(fmtDayMonthYear('2026-10-26T23:30:00Z')).toBe('26-10-2026');
    expect(fmtDayMonthYear('2026-10-27T01:30:00+05:30')).toBe('26-10-2026');
    expect(fmtDayMonthYear('2026-10-26T23:30:00')).toBe('26-10-2026');
  });
  it('handles absent or invalid timestamps',()=>{
    expect(fmtDayMonthYear(null)).toBe('—');
    expect(fmtDayMonthYear('invalid')).toBe('invalid');
  });
});
