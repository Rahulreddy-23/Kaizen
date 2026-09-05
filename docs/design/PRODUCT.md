# PRODUCT.md — Kaizen Cross-Check

Product truth for anyone designing or building the reviewer interface. Visual decisions live in
[DESIGN.md](DESIGN.md).

## What it is

A local quality-engineering tool for BD (Becton Dickinson) sustenance engineering. It cross-checks the
documents behind a medical kit SKU — the JDE bill of materials, the product label, the packaging drawing
and the product change order — pairs the lines, classifies every comparison, and gives two reviewers the
evidence to decide. The engine recommends; the reviewer decides. Every value on screen is traceable to a
file, a page and a box.

## Who uses it, where

- **BOM facilitator (reviewer 1).** R&D or quality engineer preparing a change-control review. Works
  through a queue of a few hundred comparisons per project, several projects a year. Wants to clear the
  obvious quickly and spend time where the engine is unsure.
- **Independent reviewer (reviewer 2).** Quality reviewer who is only free a few hours a day and must
  review *blind*: they cannot see reviewer 1's decisions until they have recorded their own.
- **Problem owners and judges** watching a demo, who need to understand the picture in seconds.

Used on a laptop or a desktop monitor in office light, mouse and keyboard, often for an hour at a time.
Never on a phone. Sometimes offline, so nothing may depend on the network (fonts and icons ship with
the app).

## The job

1. Load a folder of documents and see, at a glance, what the engine cleared and what needs a person.
2. Work the queue: open a comparison, see both documents with the exact lines highlighted, read why the
   engine classified it that way, decide, move to the next one without touching the mouse.
3. Turn a confirmed pairing into a terminology relationship so the next SKU clears itself.
4. Review blind as reviewer 2, resolve disagreements, finalise.
5. Export the traceable workbook, the annotated BOM and the per-SKU certificate; compare runs after
   corrected documents come back; read the business case.

## What must stay true

- The engine's recommendation is always visible and never replaced by a decision.
- Classification, severity and review state are meaning, carried by colour **and** words.
- Reviewer identity, slot and blind mode are server-side; the interface reflects them, never chooses them.
- Every count and every claim on screen comes from the run. Nothing is decorative data.
- Keyboard-first review must keep working: `j`/`k`, `Enter`, `a`/`c`/`o`/`n`, `Esc`, `?`.
- Routes, API calls and functionality are fixed; the redesign changes how things look and how clearly
  they read, not what they do.

## Voice

Plain, specific, sentence case. Controls name their action ("Record decision", "Export workbook").
Errors name the problem and the recovery. No exclamation marks, no "oops", no marketing words.
