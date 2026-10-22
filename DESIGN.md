---
name: Agent Delegation Ledger
description: Implemented utilitarian delegation inspection interface
colors:
  paper: "#f3f4f1"
  ink: "#202c28"
  muted: "#52615a"
  line: "#cbd2cc"
  accent: "#24563e"
  accent-hover: "#193d2c"
  focus: "#a4471c"
  field: "#fff"
  field-border: "#8d9c92"
  secondary-border: "#8b9e90"
  secondary-hover: "#e0e8df"
  inset: "#e7ece5"
typography:
  body:
    fontFamily: '"Segoe UI", system-ui, sans-serif'
    fontSize: "15px"
  title:
    fontFamily: '"Segoe UI", system-ui, sans-serif'
    fontSize: "20px"
    letterSpacing: "-.02em"
  label:
    fontFamily: '"Segoe UI", system-ui, sans-serif'
    fontSize: "14px"
    fontWeight: 550
  evidence:
    fontFamily: "ui-monospace, monospace"
    fontSize: "11px"
    lineHeight: 1.65
rounded:
  control: "4px"
spacing:
  action-gap: "8px"
  section-gap: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.field}"
    rounded: "{rounded.control}"
    padding: "10px 13px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "10px 13px"
  input:
    backgroundColor: "{colors.field}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 11px"
---

# Design System: Agent Delegation Ledger

## Overview

**Creative North Star: "Delegation Ledger"**

The implemented Operate interface uses muted paper, green actions and ruled sections. English controls, visible document previews and compact evidence records support inspection of a synthetic delegation case. The approved three-panel architecture is preserved.

Recorded from the dashboard template, stylesheet and desktop, tablet and mobile captures in `artifacts/ledger-*.png`. These are implementation observations, not a visual-comp comparison or owner UAT result.

**Key Characteristics:**
- Flat paper surfaces with ruled boundaries.
- Green controls and explicit textual states.
- Dense, expandable evidence with wrapping identifiers.

## Colors

### Primary
Muted green marks actionable controls, outlined secondary actions and the synthetic-demo badge. Its darker variant is the primary hover state. Orange is reserved for keyboard focus.

### Neutral
Paper is the page ground; ink is primary text; muted green-gray supports explanations and metadata. Fine lines divide panels and records. White fields have stronger borders. Pale inset surfaces contain previews and signed JSON; secondary hover adds a subtle green tint. Feedback uses the implemented pale green fill without assigning a separate success or error color.

**The Text Verdict Rule.** State meaning is carried by words and reason codes, not color alone.

## Typography

System UI supports English controls without downloaded fonts. Body text uses the frontmatter stack; explanatory paragraphs use generous line height (1.6). The page heading is modest (25px, weight 650), panel headings are smaller (20px), record headings smaller again (16px), and supporting text is compact (13px). Labels remain distinct (14px, weight 550). Code uses the evidence role; expanded JSON has line height (1.7).

**The Evidence Type Rule.** Monospace is reserved for hashes, IDs and signed data.

## Layout

The dashboard has permissions, event chain and receiver inbox in that order. Desktop columns use proportions (1.08 / 1.25 / 0.85), with no fixed page-width cap. Sections use padding (26px 24px 40px); the header uses broad horizontal padding (32px). Actions wrap with the action-gap token.

At widths up to (1000px), permissions and events share two equal columns and the inbox spans the next row. At widths up to (640px), all three stack in source order, section padding becomes (24px 20px), and the header badge follows the title block. Long identifiers wrap anywhere. Signed JSON scrolls vertically beyond (350px).

## Elevation & Depth

There are no shadows. Dividers establish hierarchy; pale filled insets distinguish document previews and signed data from the page. Records remain flat and begin with a horizontal rule.

**The Ruled Surface Rule.** Separate records through spacing and fine boundaries rather than lifted cards.

## Shapes

Fields and buttons have gently rounded control corners, as specified in frontmatter. Preview blocks, panels and record regions remain square. Borders are thin (1px); focus uses an offset outline (3px, offset 3px).

## Components

- **Buttons:** compact, solid green primary actions and transparent outlined secondary actions. Hover darkens primary actions or tints secondary actions. Disabled buttons use opacity (.6) and a wait cursor. The same treatment covers download links.
- **Fields:** full-width white inputs and selects with visible labels, green caret and the common focus outline. The delegation checkbox uses the action accent.
- **Document preview:** a pale inset contains document text, version and wrapping hash before approval.
- **Records and event rows:** thin top borders separate grants, attempts, inbox messages and signed events. Definition lists align labels with values; event counts and metadata use muted text.
- **Disclosure:** native details/summary exposes signed JSON, receiver receipts and optional checks. Summary remains a compact text control with visible keyboard focus.
- **Feedback:** a polite live-status region expands when populated. Unknown delivery state includes text and a receipt-reconciliation action; receiver unavailability has alert semantics.

## Do's and Don'ts

- Do keep controls explicitly labeled in English and preserve visible keyboard focus.
- Do wrap hashes and signed data within their available width.
- Do express delivery verdicts and uncertainty in text.
- Don't substitute decorative status color for a textual verdict.
- Don't add external fonts or imagery to this utilitarian surface.
