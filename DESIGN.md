---
version: alpha
name: EZPowers Workflow Atlas
description: "Normative visual tokens and implementation guardrails for the repository's Korean HTML skill guide."
colors:
  primary: "#315bdc"
  primary-deep: "#2143ab"
  primary-soft: "#e9eeff"
  canvas: "#f2efe7"
  canvas-deep: "#e7e2d6"
  paper: "#fffdf8"
  paper-raised: "#ffffff"
  ink: "#172033"
  ink-soft: "#344057"
  muted: "#687286"
  faint: "#8991a0"
  line: "#d9d5ca"
  line-strong: "#c4bfb2"
  mint: "#087c70"
  mint-soft: "#dcf5ee"
  amber: "#a95e0a"
  amber-soft: "#fff0d4"
  coral: "#b84740"
  coral-soft: "#ffe8e4"
  violet: "#6b50bd"
  violet-soft: "#eee9ff"
  code: "#131c2e"
  code-ink: "#eff4ff"
  focus: "#0a74ff"
  dark-primary: "#84a1ff"
  dark-primary-deep: "#b1c2ff"
  dark-primary-soft: "#253359"
  dark-canvas: "#10151f"
  dark-canvas-deep: "#0a0f17"
  dark-paper: "#171e2a"
  dark-paper-raised: "#1c2533"
  dark-ink: "#f3f5f9"
  dark-ink-soft: "#d7deea"
  dark-muted: "#a8b3c3"
  dark-faint: "#7f8a9b"
  dark-line: "#303a49"
  dark-line-strong: "#465164"
  dark-mint: "#68d8c8"
  dark-mint-soft: "#173e3a"
  dark-amber: "#f1b45e"
  dark-amber-soft: "#493518"
  dark-coral: "#ff938b"
  dark-coral-soft: "#4b2828"
  dark-violet: "#bda8ff"
  dark-violet-soft: "#342c54"
  dark-code: "#090e17"
  dark-code-ink: "#edf2ff"
  dark-focus: "#83b4ff"
typography:
  body:
    fontFamily: "Pretendard, Noto Sans KR, Apple SD Gothic Neo, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.7
  display:
    fontFamily: "Iowan Old Style, Noto Serif KR, Nanum Myeongjo, Georgia, ui-serif, serif"
    fontSize: 2.7rem
    fontWeight: 700
    lineHeight: 0.98
  heading:
    fontFamily: "Iowan Old Style, Noto Serif KR, Nanum Myeongjo, Georgia, ui-serif, serif"
    fontSize: 2rem
    fontWeight: 700
    lineHeight: 1.08
  code:
    fontFamily: "SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace"
    fontSize: 0.88rem
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: 12px
  md: 18px
  lg: 28px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 64px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.paper-raised}"
    rounded: "{rounded.full}"
    padding: 12px
  card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  code-block:
    backgroundColor: "{colors.code}"
    textColor: "{colors.code-ink}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
---

# EZPowers Workflow Atlas Design System

## Overview

The guide is a calm, editorial workflow atlas: warm paper surfaces, restrained
blue interaction color, serif display headings, and compact technical details.
It must remain readable as a single offline HTML document in Korean and should
feel like durable project documentation rather than a marketing landing page.
The machine-readable tokens above are normative. The broader UX, state,
responsive, accessibility, and visual-QA contract remains in
`docs/ux/frontend-design.md`.

This profile selectively follows Google design.md's alpha format as reviewed at
commit `9bf8eae67128b6cc55ad9bf86665767deb4c11cd`; EZPowers' installed profile and
offline validator define the supported maintenance contract.

## Colors

Light mode uses `canvas` behind `paper` surfaces, `ink` for primary text, and
`primary` for the dominant action. Mint, amber, coral, and violet communicate
workflow categories, not decoration. Dark-mode tokens use the `dark-` prefix
and map one-for-one to the same CSS custom properties under
`html[data-theme="dark"]`. Focus rings always use `focus` or `dark-focus`.

## Typography

Korean long-form content uses the `body` sans-serif stack at 16px and 1.7 line
height. Display and section headings use the serif stack to create hierarchy;
commands and invocation examples use `code`. System fallbacks are intentional,
so the document stays self-contained without remote font requests.

## Layout

Use the spacing scale for component gaps and padding. The page combines a
persistent desktop navigation rail with a linear reading column; smaller
viewports collapse navigation without hiding content or changing workflow
order. Content must remain usable at the 280px minimum width implemented by the
guide.

## Elevation & Depth

Hierarchy comes primarily from paper tone, borders, and spacing. Large panels
may use the existing `--shadow` value and compact interactive surfaces may use
`--shadow-small`; neither shadow is a license to add new floating layers.
Dark mode uses the corresponding shadow overrides already defined in the HTML.

## Shapes

Use `sm` for small controls and code blocks, `md` for cards, and `lg` for major
feature panels. `full` is reserved for pills and circular controls. One-off
radii already present in the HTML may remain where geometry requires them, but
new reusable components must select the nearest named token.

## Components

Primary buttons, cards, and code blocks use the component mappings above.
Interactive components must define visible hover/focus behavior and preserve
the guide's keyboard navigation. Category colors may identify a workflow lane,
but primary actions remain blue and semantic error/success meaning must not be
encoded by color alone.

## Do's and Don'ts

- Do update this file first when an intentional token or reusable component
  rule changes, then align the HTML and the broader frontend-design artifact.
- Do retain light and dark mode parity and the 3px visible focus outline.
- Do review token removals and newly introduced warnings with `design-md.py
  diff` before accepting a visual-system change.
- Don't introduce remote fonts, scripts, or image dependencies into the
  self-contained guide.
- Don't treat mockups or screenshots as a stronger source of truth than this
  file and the repository-owned frontend design contract.
