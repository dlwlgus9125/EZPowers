---
name: deep-interview
description: Use when a user's request is vague, underspecified, solution-shaped, or explicitly asks for deep-interview, requirement clarification, "grill me", or "그릴미". Resolve stated ambiguity and consequential blind spots into a confirmed, decision-ready request, then offer to proceed, correct, or finish with the summary. Proceed resumes host work in ordinary mode or planning in active Plan Mode. Not for reviewing artifacts or small concrete edits whose scope and success are already settled.
---

# Deep Interview

Turn a request into a decision-ready request the user recognizes as their own.
Find consequential unspoken assumptions as well as stated ambiguity, without
turning the conversation into an exhaustive audit or specification.

## Keep it session-only

Keep clarification in the current conversation. Do not create or update files
during the interview. Do not assume that any companion skill, workflow,
runtime, contract, or project artifact exists. The interview does not dispatch
another skill or workflow. After a proceed choice, the interview ends and the
host resumes the approved work under its current mode, project instructions,
and permissions.

## Build a grounded provisional request

1. Inspect project or artifact evidence before factual questions. Separate
   discoverable facts from user choices; cite relevant paths, symbols, or
   behavior rather than asking the user to rediscover facts.
2. Maintain a provisional request covering relevant outcomes, people, systems,
   problems, scope, non-goals, constraints, and observable success. Treat it as
   a falsifiable hypothesis, not a user decision.
3. Separate outcomes from proposed means. Determine whether the means is
   required or tentative. Challenge framing only when evidence or credible
   consequences make it material; offer the strongest alternative or tradeoff.

## Run two silent passes

Before every question and before stopping, run both passes:

1. **Explicit-gap pass:** Find what is unclear, multiply defined, or missing
   such that rewriting it would invent a preference. Check each independently
   useful part of a multi-part request.
2. **Blind-spot pass:** Try to falsify the provisional request from outside its
   framing. Generate context-specific candidates from hidden assumptions or
   alternative frames; omitted people, systems, or dependencies; boundaries,
   failure, misuse, or compatibility; and downstream or hard-to-reverse
   consequences.

Treat these as reasoning lenses, not a questionnaire. Ask about a blind spot
only when it is both:

- **plausible:** grounded in the request, available evidence, or a credible
  domain consequence, not a bare possibility; and
- **consequential:** its answer could materially change the outcome, scope,
  constraints, non-goals, success, or approach.

For high-stakes or hard-to-reverse decisions, a credible severe failure can be
consequential even when uncommon. Discard settled points, discoverable facts,
speculative trivia, and later implementation details. The internal blind-spot
pass is mandatory; an external blind-spot question is not.

## Interview loop

1. Rank explicit gaps and eligible blind spots together. Select the single
   unresolved point with the greatest combination of impact and uncertainty.
2. Ask exactly one question, then wait for the answer. Never bundle questions.
3. When useful, state the provisional hypothesis, why the answer matters, and
   a recommended answer or alternative with its main tradeoff.
4. Prefer an open question when predefined choices would anchor the answer.
   Use choices only for real, distinct alternatives and permit free-text
   correction.
5. After each answer, update the provisional request without inventing a
   preference. If the answer stays superficial, use one focused probe such as
   an example, counterexample, hidden assumption, boundary, tradeoff, simplest
   useful version, or reframing.

Do not report a numerical ambiguity or risk score. Do not expose
the candidate list or ask the user to perform the analysis. Do not implement or
write artifacts during the interview. Use a native structured question surface
when callable; otherwise ask one plain-text question.

## Stop and confirm

Stop asking when:

- rewriting requires no invented user preference;
- neither pass finds a material gap or plausible consequential blind spot;
- all independently useful parts of the request have been checked.

Present **Clarified request** as a self-contained replacement in the user's
language and voice. Include settled intent and material assumptions, non-goals,
constraints, and success signals; omit the transcript and irrelevant rejected
alternatives.

Ask one question combining confirmation and continuation, with these choices
in the user's language:

- **Confirm and proceed** (recommended): in ordinary mode, carry out the
  clarified request, including implementation and verification when requested.
- **Correct**: revise the request and obtain confirmation again.
- **Confirm and finish with summary**: retain the confirmed request and stop.

In Plan Mode, replace the first choice with **Confirm and continue planning**
and explicitly state that it continues planning only. Use a native structured
question surface callable in the current mode, otherwise present the same
choices in one plain-text question. Do not switch modes to obtain a question UI.
Wait for the submitted answer, including with asynchronous question tools.
Preselection, silence, and agreement with the wording alone are not permission
to proceed; clarify the action if needed. The interview is complete only after
explicit confirmation. Respect an explicit summary-only or stop request.

## Continue according to the choice

Treat **Clarified request** as the source of truth for clarified user intent,
carrying its scope, constraints, assumptions, and success criteria forward.
Do not repeat settled product questions.

- **Ordinary-mode proceed:** end the interview and immediately resume the
  host's normal work on the request through completion and relevant checks.
  Do not end with only a summary or require another command; do not add a
  second continuation question after approval. Subsequent work may write files
  within the approved request; it does not require a particular companion
  workflow or grant broader permissions.
- **Plan-mode proceed:** immediately resume the host's native planning process.
  Produce the native final plan when decision-complete, otherwise resolve only
  remaining implementation decisions. Do not start implementation. If Plan
  Mode is no longer active, its planning confirmation still does not authorize
  implementation; any later execution needs its own user authorization.
- **Correction or finish:** correction returns to clarification without work;
  summary-only ends without execution. If the user ends the interview early,
  provide the best current request, mark material unresolved points, and stop
  without claiming full clarification or taking a next step.
