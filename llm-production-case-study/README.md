# LLM integrations in production — three case studies

Three LLM systems I designed, shipped and operate in production, on two different providers
(DeepSeek and Anthropic). What they share is the part most LLM demos skip: **cost budgets,
latency budgets, code-level verification of model output, and measured behavior.** The model
is treated as a component with an SLA, not a magic box.

---

## Case 1 — Customer-facing support agent (DeepSeek, function calling)

A support agent embedded in a live marketplace website, answering authenticated users in
three languages (es/en/fr), able to look up each user's own orders, payout method, refund
status and more through function calling.

**Engineering highlights**

- **The engine is pure, side-effect code is injected.** The chat module only knows how to
  talk to the API and run the function-calling loop; each tool's real implementation is
  passed in as a callback. The module is readable and testable without a database.
- **Model selection by cost.** A fast, cheap model handles normal traffic; a stronger model
  is configured as fallback and is only paid for on the messages that need it.
- **Measured failover.** On a day when the primary model started leaving requests queued for
  the full timeout, traffic was switched to the fallback (1–5 s responses) — so the code now
  times the primary out at 20 s, routes to the fallback for a 5-minute cooldown, then retries
  the primary. Every threshold is a measured number, documented inline with the date.
- **History and token caps** bound per-session cost; the frontend can still display the full
  transcript.
- **Graceful degradation**: with no API key configured, the endpoint ships a "setting up"
  notice instead of failing, so the surrounding system can be deployed and tested first.

## Case 2 — Vision verification as an independent second reader (Anthropic)

An optional, isolated layer that reads the **same source image** a primary OCR reads, to give
an independent second reading — two different readers rarely make the same mistake, so
requiring agreement *tightens* a gate instead of loosening it.

**Engineering highlights**

- **Three run modes** (`off` / `shadow` / `active`): off spends nothing and returns `None`;
  shadow calls the API and logs the verdict without acting on it (pure observation in
  production); active lets the verdict into the decision. This makes it safe to measure a new
  model against real traffic before trusting it.
- **Model choice per job**: a stronger model for precision-critical reads, a cheap model for
  classification — paying for capability only where it changes the outcome.
- **Structured output only.** The model can return only a bounded JSON verdict; its result is
  never wired directly to an action. On any error it returns `None` (fail-safe).
- **The matching stays exact.** The model acts as a second OCR, not a fuzzy threshold — it
  rescues a read the primary OCR missed, it does not relax the check.

## Case 3 — Human-like async responder (code-level verification)

A module that decides when and how to reply to incoming chat as a busy person would, with a
per-session "mood" chosen at startup for a consistent voice.

**Engineering highlights**

- **What must be measurable is done in code, not in the prompt.** Probabilities (whether to
  reply at all, per channel; typo rate; reply length bias) are applied *outside* the model,
  so they can be counted and tuned. A model can't reliably roll a weighted die; code can.
- **A non-LLM safety net** handles the case where the model declines or is unavailable, so
  the feature degrades instead of breaking.
- **Multi-language handling by a discriminated lexicon** — replies land in the language the
  message came in, and the behavior was validated with a 20,000-encounter simulation over the
  real code before shipping.
- **Human-plausible timing**: reading time scales with message length, typing time with reply
  length, under a hard response-time cap — a one-character reply is instant, a sentence is not.

---

## The thread through all three

1. **Cost and latency are design inputs**, not afterthoughts — model choice, timeouts,
   fallbacks and caps are all decided from measured numbers.
2. **Verification is in code, structured output, and fail-safe defaults** — the model advises;
   it never directly triggers an irreversible action.
3. **Shadow/observation modes** let a change be measured against real traffic before it is
   trusted.

*(Code excerpts available on request — the production source is sanitized before sharing.)*
