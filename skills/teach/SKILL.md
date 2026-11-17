---
name: teach
description: Explicitly teach the user one skill or concept across multiple sessions, treating the directory the skill is invoked in as a stateful teaching workspace of mission, vetted resources, short HTML lessons, reference documents, and learning records. Use when the learning itself is the project; not for a one-off explanation, project documentation, or work inside an EZPowers-managed project.
disable-model-invocation: true
---

# Teach

The user has asked you to teach them something. This is a stateful request:
they intend to learn the topic over multiple sessions, and the state of that
learning lives in files, not in the conversation.

## Resolve two roots

- `<skill-root>` is the directory containing this `SKILL.md`. It is read-only.
  The format references live in `<skill-root>/references/`. Never write a
  workspace file under `<skill-root>`, and never fetch an upstream file at
  runtime. If the host cannot read a reference, tell the user and ask for read
  access to `<skill-root>` before writing the workspace file that reference
  governs; do not improvise its format.
- `<workspace>` is the directory the user invoked this skill in. Every
  workspace path below (`MISSION.md`, `lessons/`, and the rest) resolves from
  `<workspace>`.

## Guard the workspace before the first write

A teaching workspace takes over its directory and holds exactly one mission.
Before creating or changing any file, find the Git worktree root that contains
`<workspace>`, if there is one. If that root contains a `.ezpowers/`
directory, `<workspace>` is inside an EZPowers-managed project: stop, explain
that lesson files there change the project's workspace and make its completion
evidence stale, and ask the user for a dedicated teaching directory. Continue
in the current directory only when the user explicitly chooses it after that
warning, and record the choice in `NOTES.md` so later sessions do not ask
again.

## Teaching workspace

The state of the user's learning is captured in `<workspace>`:

- `MISSION.md`: the _reason_ the user is interested in the topic. It grounds
  all teaching. Use the format in `<skill-root>/references/mission-format.md`.
- `RESOURCES.md`: the resources that ground your teaching in contextual
  knowledge and lead the user to knowledge and wisdom. Use the format in
  `<skill-root>/references/resources-format.md`.
- `GLOSSARY.md`: the canonical terminology for the topic, created once the
  topic has its own nomenclature. Use the format in
  `<skill-root>/references/glossary-format.md`.
- `learning-records/*.md`: what the user has learned. These are loosely
  equivalent to architectural decision records: they capture non-obvious
  lessons and key insights that may be revised later or drive future
  sessions, and they are used to calculate the zone of proximal development.
  They are titled `0001-<dash-case-name>.md`, where the number increments each
  time. Use the format in `<skill-root>/references/learning-record-format.md`.
- `lessons/*.html`: the lessons. A **lesson** is a single HTML output that
  teaches one tightly-scoped thing tied to the mission. It is the primary unit
  of teaching in this workspace.
- `reference/*.html`: the compressed learnings from the lessons, such as cheat
  sheets, reference algorithms, syntax, and pose sequences. They are the raw
  units of learning: beautiful documents that print well and are designed for
  quick reference.
- `assets/*`: reusable **components** shared across lessons. See
  [Assets](#assets).
- `NOTES.md`: a scratchpad for the user's teaching preferences and your
  working notes.

Write lessons, reference documents, questions, and workspace prose in the
user's active conversational language unless the user names another language.
Keep the file and directory names above unchanged.

## Philosophy

To learn at a deep level, the user needs three things:

- **Knowledge**, captured from high-quality, high-trust resources
- **Skills**, acquired through highly-relevant interactive lessons devised by
  you, based on the knowledge
- **Wisdom**, which comes from interacting with other learners and
  practitioners

Before `RESOURCES.md` is well-populated, your focus should be to find
high-quality resources that will help the user acquire knowledge. Never trust
your parametric knowledge.

Some topics require more skills than knowledge. Learning more about
theoretical physics is more knowledge-based. Yoga is more skills-based.

### Fluency versus storage strength

Separate two types of learning:

- **Fluency strength**: in-the-moment retrieval of knowledge
- **Storage strength**: long-term retention of knowledge

Fluency can give the user an illusory sense of mastery, but storage strength
is the real goal. Design lessons that build long-term retention through
desirable difficulty:

- Retrieval practice (recall from memory)
- Spacing (distributing practice over time)
- Interleaving (mixing different but related topics, for skills practice only)

## Lessons

A lesson is the main thing you produce: the unit in which knowledge and skills
reach the user. Each lesson is one HTML file, saved to `lessons/` and titled
`0001-<dash-case-name>.html`, where the number increments each time.

A lesson should be **beautiful**, with clean, readable typography and layout,
since the user will return to it later to review. Think Tufte.

A lesson should be short and completable very quickly. Learners' working
memory is very small, and the lesson must stay within it. Each lesson should
still give the user a single tangible win that they can build on. It should be
directly tied to the mission and sit in the user's zone of proximal
development.

When the host can run commands, open the lesson file for the user with the
operating system's default handler (`Start-Process` on Windows, `open` on
macOS, `xdg-open` on Linux). Otherwise give the user the file path.

Each lesson should link via HTML anchors to other lessons and reference
documents.

Each lesson should recommend a primary source for the user to read or watch:
the most high-quality, high-trust resource you found on the topic.

Each lesson should contain a reminder to ask the agent follow-up questions.
The agent is their teacher and can assist with anything that is unclear.

## Assets

Lessons are built from reusable **components**, stored in `assets/`:
stylesheets, quiz widgets, simulators, diagram helpers, and anything else a
second lesson could reuse.

Reuse is the default, not the exception. Before authoring a lesson, read
`assets/` and build from the components already there. When a lesson needs
something new and reusable, write it as a component in `assets/` and link to
it; never inline code a future lesson would duplicate.

A shared stylesheet is the first component every workspace earns: every lesson
links it, so the lessons look like one consistent course rather than a pile of
one-offs. As the workspace grows, so should the component library.

## The mission

Every lesson should be tied to the mission: the reason the user is interested
in learning the topic.

If the user is unclear about the mission, or `MISSION.md` is not populated,
your first job is to question the user on why they want to learn this. Do not
produce a lesson before the mission is recorded.

Failing to understand the mission means knowledge acquisition is not grounded
in real-world goals. Lessons will feel too abstract, and you will have no way
of judging what the user should do next.

Missions may change as the user develops more skills and knowledge. This is
normal: update `MISSION.md` and add a learning record to capture the change.
Confirm with the user before changing the mission.

## Zone of proximal development

In each lesson the user should feel challenged just enough.

The user may specify an exact thing they want to learn. If they do not, find
their zone of proximal development by:

- Reading their learning records
- Working out the right thing to teach them based on their mission
- Teaching the most relevant thing that fits that zone

## Knowledge

Design each lesson around a skill the user is going to learn. The knowledge in
the lesson should be only what is required to acquire that skill. Teach the
knowledge first, then have the user practice the skill through an interactive
feedback loop.

Gather knowledge from trusted resources first, and track them in
`RESOURCES.md`. Lessons should be littered with citations: links to external
resources that back up each claim. This increases the trustworthiness of the
lesson.

Use the host's web search and fetch tools to find and check resources. If the
host has no web access, say so, ask the user to supply sources, and mark a
claim you could not check as unverified instead of presenting it as sourced.

For acquiring knowledge, difficulty is the enemy. It eats the working memory
the user needs for understanding.

## Skills

If knowledge is about acquisition, skills are about durability and
flexibility. Make the knowledge stick.

For skill acquisition, difficulty is the tool. Effortful retrieval is what
builds storage strength. Teach skills through interactive lessons:

- Interactive lessons, using quizzes and light in-browser tasks
- Lessons that guide the user through a list of real-world steps to take (for
  instance, yoga poses)

Base each of these on a **feedback loop**, where the user receives feedback on
their performance. Keep the loop as tight as possible: immediate, and ideally
automatic.

For quizzes, each answer should be exactly the same number of words (and
characters, if possible). Never rely on authored order to hide the correct
answer: the quiz component in `assets/` must shuffle the answer options in the
browser each time a question renders. Do not give the user any clue about the
answer through formatting or order.

## Acquiring wisdom

Wisdom comes from real-world interaction: testing skills outside the learning
environment.

When the user asks a question that appears to require wisdom, your default
posture is to attempt an answer, but ultimately to delegate to a
**community**.

A community is a place, online or offline, where the user can test their
skills in the real world. This might be a forum, a subreddit, a real-world
class (budget permitting), or a local interest group.

Try to find high-reputation communities the user can join. If the user
expresses a preference not to join a community, respect it.

## Reference documents

While creating lessons, also create reference documents. Lessons can link to
them; they track the raw units of knowledge that are useful across lessons.

Lessons will rarely be revisited later; reference documents will be. They
should be the compressed essence of a lesson, in a format designed for quick
reference.

Some learning topics lend themselves to reference:

- Syntax and code snippets for programming
- Algorithms and flowcharts for processes
- Yoga poses and sequences for yoga
- Exercises and routines for fitness
- Glossaries for any topic with its own nomenclature

Glossaries, in particular, are an essential reference. Keep the canonical
terms in `GLOSSARY.md`; once it exists, adhere to it in every lesson and
reference document.

## `NOTES.md`

The user will sometimes express preferences for how they want to be taught, or
things you should keep in mind. Record them here so you can refer back to them
when designing lessons or working with the user.

## Boundaries

This skill adds no workflow transition, verification, completion authority, or
project documentation. It writes only inside the teaching workspace and never
to `.ezpowers/`, a project wiki, specs, or plans.

Adaptation notice: this file is a modified EZPowers adaptation of Matt
Pocock's `teach` skill; see `LICENSE` in this skill directory.
