# EZPowers Skill Guide Frontend Design

## Surface, audience, and intent

- **Surface:** a self-contained, static HTML guide at
  `docs/ezpowers-skills-guide.html`.
- **Primary audience:** Korean-speaking Claude Code and Codex users who know
  the project goal but do not yet know which EZPowers skill to invoke.
- **Secondary audience:** maintainers checking the boundary between plugin
  skills, project-installed skills, ordinary execution, and the explicit
  harness chain.
- **Outcome:** a reader can identify the next skill, copy the correct
  host-specific invocation, understand what artifact or verdict it produces,
  and avoid the most consequential misuse without reading every contract
  first.
- **Delegation:** the user requested high readability and visual quality
  without prescribing a visual direction, so the final direction is delegated
  to the implementer.

## Considered directions

### A. Technical command center

A dark, dense dashboard with status chips, terminal motifs, and compact data
tables.

- Strength: immediately communicates developer tooling and supports dense
  scanning.
- Tradeoff: long Korean explanations become tiring, and a dark-only surface is
  less suitable for printing or documentation reading.

### B. Editorial field manual

A warm paper palette, serif display type, generous margins, and long-form
chapter navigation.

- Strength: excellent sustained readability and a calm documentation tone.
- Tradeoff: workflow branching and operational differences are less visible,
  and the result can feel static.

### C. Workflow atlas — selected

An editorial reading surface combined with route-map visualization, compact
skill cards, and host-aware command examples.

- Strength: keeps prose comfortable while making the ordinary path, optional
  branches, explicit chain, and global HUD visibly distinct.
- Tradeoff: requires disciplined color semantics and responsive flow layout so
  the map does not become decorative noise.

The selected direction uses a warm neutral canvas, near-black ink, cobalt for
the ordinary workflow, mint for supporting knowledge, amber for decisions,
and coral only for cautions. Dark mode preserves the same semantic hierarchy.

## Information architecture

The single page contains:

1. **Hero and quick start:** version, scope, ordinary recommended sequence,
   and host selector.
2. **Invocation boundary:** plugin namespace versus installed project-local
   syntax for Claude Code and Codex.
3. **Main workflow map:** setup, optional clarification/design branches, spec,
   plan, execute, verify, and certify.
4. **Decision helper:** common user situations mapped to the first relevant
   skill.
5. **Skill catalog:** all thirteen plugin skills with purpose, trigger, non-goal,
   output, invocation, and key caution.
6. **Recipes:** standard feature, ambiguous request, UI feature, diagnosis,
   architecture improvement, and explicit unattended chain.
7. **Harness-chain map:** configure, preview/audit, one approval, native loop,
   verification, independent gates, and terminal verdict.
8. **Boundaries and glossary:** host ownership, local evidence, certification,
   supporting wiki memory, and global-only HUD.

The page has a desktop sticky table of contents and a compact mobile header.
Section anchors work without JavaScript.

## State matrix

| Surface | Default | Hover/focus | Selected/active | Empty/error |
| --- | --- | --- | --- | --- |
| Host selector | Codex | Raised outline | Filled cobalt tab | Not applicable; one host is always selected |
| Theme control | System-derived light | Raised outline | Icon and accessible label update | Falls back to light if storage is unavailable |
| Skill search | Empty query | Cobalt focus ring | Matching count updates | A no-results panel offers query reset |
| Category filters | All | Raised outline | Filled category chip | All remains available |
| Skill card | Summary visible | Border and elevation increase | Search match remains normal; nonmatches hide | Search no-results handled at catalog level |
| Details disclosure | Closed | Summary highlight | Expanded explanation and examples | Native disclosure works without JavaScript |
| Copy command | Copy label | Cobalt focus ring | Brief “copied” confirmation | Selects text/fallback message if clipboard is unavailable |
| Workflow node | Static | Related route emphasis | Not applicable | Not applicable |

Loading, offline, permission, cancellation, and long-running states are not
applicable because the guide has no network request or asynchronous data
dependency. JavaScript is progressive enhancement only; all content and links
remain available when it is disabled.

## Design tokens and primitive policy

The repository has no existing frontend system. The guide therefore owns a
small inline token set:

- color tokens for canvas, elevated paper, ink, muted text, lines, workflow,
  supporting knowledge, decisions, cautions, and code;
- a system Korean sans-serif stack for body text and a system serif stack for
  display headings, with no external font request;
- an 8 px spacing basis with a restrained responsive type scale;
- 14–24 px corner radii, one subtle paper shadow, and 2 px focus outlines;
- motion limited to opacity, transform, and color changes under 180 ms, fully
  disabled by `prefers-reduced-motion`.

Primitives are semantic HTML elements, CSS grid/flex layouts, buttons, links,
`details`/`summary`, code blocks, and inline SVG. No framework, remote script,
icon package, or webfont is introduced.

## Component taxonomy

- `site-header`: brand, version, theme toggle, and compact navigation.
- `hero`: title, promise, ordinary path summary, and quick actions.
- `host-switcher`: Claude/Codex choice that rewrites visible invocation
  examples without hiding conceptual content.
- `route-map`: ordered nodes, conditional gates, supporting orbit, and
  explicit-only branch.
- `decision-grid`: task-shaped entry points with the recommended first skill.
- `skill-toolbar`: search, filters, and result count.
- `skill-card`: category, scope badge, purpose, when-to-use signal, output,
  non-goal, command, and expandable operational notes.
- `recipe`: a short ordered path with optional branches.
- `chain-map`: approval and evidence-gated unattended sequence.
- `boundary-callout`: do/don't pairs for responsibility and authority.
- `footer`: source-of-truth links and document version.

Every interactive component has a visible keyboard focus state. Color is
reinforced by labels, shape, or placement.

## Responsive and input rules

- **≥ 1180 px:** sticky left rail plus main reading column; skill catalog uses
  two columns.
- **760–1179 px:** top navigation, full-width reading column, two-column cards
  where space allows.
- **< 760 px:** one-column cards, horizontally wrapping host/filter controls,
  and workflow nodes stacked vertically with downward connectors.
- **< 420 px:** tighter page gutters and full-width command/copy controls.
- Pointer hover is supplemental. All actions work with keyboard and touch.
- The page must not introduce horizontal scrolling at 390 px; long commands
  wrap or scroll only inside their code container.
- Print mode removes interactive controls, uses white paper, expands
  disclosures, and preserves section ordering where browser support allows.

## Accessibility target and checks

- Target WCAG 2.2 AA for text contrast, focus visibility, semantic landmarks,
  headings, labels, and keyboard operation.
- Provide one `h1`, ordered heading levels, a skip link, labelled navigation,
  real buttons, and `aria-live` only for search/copy feedback.
- Host and category selection expose pressed/selected state.
- Inline SVGs are decorative unless they communicate route meaning; meaningful
  diagrams have adjacent text equivalents.
- Primary narrative text is at least 16 px with line height at least 1.6.
  Compact diagram annotations and metadata may use 10–12 px text only with
  strong contrast and adjacent full-text explanations. Standalone touch
  targets are at least 44 px.
- Verify keyboard traversal, 200% zoom, reduced motion, light/dark contrast,
  and no content loss without JavaScript.

## Assets and licensing

No external images, fonts, scripts, analytics, or third-party assets are used.
All decoration is CSS or original inline SVG, so there is no additional asset
provenance or licensing dependency.

## Visual QA oracle

The normative checks are:

1. Open `docs/ezpowers-skills-guide.html` directly from disk with no network.
2. Inspect at 1440×1000, 768×1024, and 390×844.
3. Confirm the main workflow, thirteen skill cards, six recipes, and chain route
   are all readable with no page-level horizontal overflow.
4. Switch Claude/Codex and verify every visible command uses the correct
   plugin namespace; switch theme and verify controls remain legible.
5. Search for a known term and a no-result term; reset the query.
6. Traverse all controls by keyboard and confirm focus visibility.
7. Disable JavaScript and confirm the full guide remains readable.
8. Run repository checks and a static content check that asserts the thirteen
   canonical skill names and both host invocation forms.

The repository does not configure a screenshot-baseline or visual-diff lane,
so screenshots are advisory evidence rather than a completion gate.

## Prototype and freshness

There is no separate mock or prototype. The HTML guide is the production
artifact. This design document is normative for its information architecture,
tokens, responsive behavior, accessibility, and visual QA.

Content freshness is bound to the canonical sources:

- `skills/*/SKILL.md` for skill behavior;
- `AGENTS.md` for the current route and responsibility boundary;
- `docs/reference/codex-plugin-discovery.md` for host invocation;
- `project-kit/v5.3.0/manifest.json` for plugin/project inventory.

When those sources change, maintainers must review both this artifact and the
HTML guide. The HTML distinguishes the v5.3.0 project kit from the v5.3.1
plugin patch rather than claiming automatic synchronization.

## Unresolved questions

None block implementation. The audience, surface, and visual direction are
settled. Localization beyond Korean labels with English command names is
outside this deliverable.
