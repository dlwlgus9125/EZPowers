---
name: deep-interview
description: Use when a user's request is vague, underspecified, solution-shaped, or explicitly asks for deep-interview, requirement clarification, "grill me", or "그릴미". Turn the request into a clear, confirmed request within the current session. Not for reviewing an existing spec, design, or plan, writing artifacts, or small concrete edits whose outcome, scope, constraints, and completion criteria are already settled.
---

# Deep Interview

Turn a vague request into a clear request the user recognizes as their own.
Clarify intent before implementation without turning the conversation into a
specification workflow.

## Keep it session-only

The interview and its result exist only in the current conversation. Do not
create or update `CONTEXT.md`, ADRs, interview briefs, specs, plans, or any other
file. Do not automatically invoke or hand off to another workflow. A later
explicitly invoked skill may use the confirmed request from this session.

## Ground the interview

1. When the request concerns an existing project or artifact, inspect enough
   repository evidence to answer factual questions before asking the user.
2. Separate discoverable facts from choices only the user can make. Never ask
   the user to rediscover repository facts.
3. Cite the path, symbol, behavior, or other evidence when it materially
   motivates a question.
4. Maintain a provisional restatement of what the user appears to want. Treat
   it as a falsifiable hypothesis, not as a user decision.
5. When the request prescribes a solution, determine whether that solution is
   a required constraint or a tentative means to the desired outcome. Do not
   discard the user's proposed solution without evidence.

## Find the consequential gaps

Silently check the request for gaps in:

- the person or system affected, the underlying problem, relevant status quo
  or workaround, and desired outcome;
- included scope, explicit non-goals, and independently useful outcomes;
- constraints, compatibility boundaries, and terms with multiple meanings;
- observable success and examples that distinguish success from failure.

Use this as an internal coverage map, not a questionnaire. Do not ask about a
dimension that is already settled or would not materially change the request.
For multi-part requests, make sure clarity in one part does not hide an
unresolved sibling.

## Interview loop

1. Select the single unresolved point with the greatest combination of impact
   and uncertainty. Do not calculate or report a numerical ambiguity score.
2. Ask exactly one question, then wait for the answer. Never bundle questions.
3. When useful, include the current hypothesis or a recommended answer and its
   consequence or tradeoff. Mark it as provisional and make correction easy.
4. Prefer an open question when predefined choices would anchor the answer.
   Use choices only when the alternatives are real and distinct, and let the
   user correct or replace them in free text.
5. Update the provisional restatement after every answer. Do not invent a
   preference to close a gap.
6. If an answer stays at the surface, pressure-test it with one focused probe:
   a concrete example, counterexample, hidden assumption, boundary case,
   tradeoff, simplest useful version, or reframing of the core problem.
7. Keep clarifying; do not implement or write project artifacts during the
   interview.

Use the current host's native structured question surface when it is callable
and appropriate. Otherwise ask one plain-text question. Never require a host or
mode change merely to present a question.

## Stop and confirm

Stop asking when all of the following are true:

- the request can be rewritten without inventing a user preference;
- no remaining question is likely to materially change the outcome, scope,
  constraints, non-goals, or observable success;
- all independently useful parts of a multi-part request have been checked.

Present **Clarified request** in the user's language as a self-contained
replacement for the original request. Preserve the user's intent and voice;
use short supporting bullets only when they make the request more usable. Ask
the user to confirm or correct it. The interview is complete only after that
explicit confirmation.

If the user ends the interview early, provide the best current clarified
request and mark only the material unresolved points. Do not claim that the
request is fully clarified, create an artifact, or suggest an automatic next
step.
