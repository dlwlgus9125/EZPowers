---
name: deep-interview
description: Use when a user's request is vague, underspecified, solution-shaped, or explicitly asks for deep-interview, requirement clarification, "grill me", or "그릴미". Turn it into a concise, confirmed, decision-ready request by resolving stated ambiguity and plausible consequential blind spots; when Plan Mode is already active, resume host-native planning after confirmation. Not for reviewing an existing spec, design, or plan, writing artifacts, or small concrete edits whose outcome, scope, constraints, and completion criteria are already settled.
---

# Deep Interview

Turn a request into a decision-ready request the user recognizes as their own.
Find consequential unspoken assumptions as well as stated ambiguity, without
turning the conversation into an exhaustive audit or specification.

## Keep it session-only

Keep the interview and its result in the current conversation. Do not create or
update `CONTEXT.md`, ADRs, briefs, specs, plans, or any other file. Do not assume
that any companion skill, workflow, runtime, contract, or project artifact
exists. Do not invoke or hand off to another skill or workflow. Outside Plan
Mode, stop after confirmation; a later explicit request may use the result.
Resuming an already active Plan Mode is continuation of the same host mode, not
a handoff.

## Build a grounded provisional request

1. For an existing project or artifact, inspect enough evidence to answer
   factual questions. Separate discoverable facts from user choices, never ask
   the user to rediscover facts, and cite the path, symbol, or behavior when it
   materially motivates a question.
2. Maintain a provisional request covering the desired outcome, affected
   people or systems, current problem, scope and non-goals, constraints, and
   observable success only as relevant. Treat it as a falsifiable hypothesis,
   not as a user decision.
3. Separate the desired outcome from any proposed means. Determine whether the
   means is a required constraint or a tentative approach. Challenge the
   framing only when evidence or a credible consequence makes that distinction
   material; then offer the strongest alternative or tradeoff.

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

Do not calculate or report a numerical ambiguity or risk score. Do not expose
the candidate list or ask the user to perform the analysis. Do not implement or
write artifacts during the interview. Use the host's native structured question
surface when callable and appropriate; otherwise ask one plain-text question.

## Stop and confirm

Stop asking when all of the following are true:

- the request can be rewritten without inventing a user preference;
- neither pass finds a material explicit gap or a plausible consequential
  unresolved blind spot;
- all independently useful parts of a multi-part request have been checked.

Present **Clarified request** in the user's language as a self-contained
replacement for the original. Preserve the user's intent and voice. Include
only the settled request and material assumptions, non-goals, constraints, or
success signals needed to act; omit the transcript and rejected alternatives
unless their absence would mislead.

Ask the user to confirm or correct it. When Plan Mode is active, say in that
same question that confirmation will continue planning. Use the host's native
structured question surface when callable, with context-appropriate equivalents
of **Confirm and continue planning** (recommended) and **Correct**; do not add a
second continuation question. The interview is complete only after explicit
confirmation.

## Resume active Plan Mode

After explicit confirmation, continue only if the host remains in Plan Mode:

1. Treat **Clarified request** as the source of truth for clarified user intent.
   Carry its goal, audience, scope, constraints, non-goals, assumptions, and
   observable success into the plan.
2. Immediately resume the host's native planning process without another
   command, skill invocation, or permission question. Do not repeat settled
   product questions; inspect facts and ask only unresolved implementation
   decisions.
3. Produce the native final plan if decision-complete; otherwise keep planning
   rather than ending with an interview-only summary.
4. Stay within the host's current Plan Mode. Do not invoke or hand off to any
   skill or workflow, create a project artifact, or start implementation.

If the user corrects the request, revise it and obtain confirmation again. If
the user ends the interview early, provide the best current clarified request
and mark only the material unresolved points. If the user asks to stop or Plan
Mode is no longer active, preserve the ordinary session-only behavior. Never
claim full clarification, create an artifact, or suggest an automatic next
step in those cases.
