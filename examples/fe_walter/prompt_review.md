# October prompt and reply comparison

This page shows the **actual saved requests** for October 12–14, 2016, in
**LLM with additional operating knowledge**. Select a date, then expand a section to read,
copy or download its complete text. No model was rerun for this review.

The system prompt, retrieved text, reply schema and provider parameters match
between Anik and HydroReOpLLM. Their user prompts differ because earlier model
replies had already changed reservoir state and decision history.

| Date | Anik: start elevation / requested release | HydroReOpLLM: start elevation / requested release |
|---|---:|---:|
| October 12 | 1250.00 ft / 50 cfs | 1336.55 ft / 1000 cfs |
| October 13 | 1269.67 ft / 50 cfs | 1328.83 ft / 1000 cfs |
| October 14 | 1274.23 ft / 50 cfs | 1319.16 ft / 1000 cfs |

## Actual requests and replies

The retrieved section is already part of the user prompt; it is repeated in its
own expandable section for inspection. The internal `target_period` record is
shown separately because it was **not included in these historical requests**.
The full payload download contains every field sent to the provider.

<div id="prompt-review" data-source="../../_static/prompt-review-data.json" data-preview="../../_static/seasonal-context-preview.json">Loading local saved evidence…</div>

Download the [complete three-day evidence](../../docs/_static/prompt-review-data.json),
including exact message strings, raw replies, source filenames, record locations
and SHA256 hashes. Full research journals remain in the external evidence archive.

## What went wrong

October 12–14 belong to the summer window. Its only pool bound is **at or below
1370 ft**. Fall drawdown starts on **October 15**. Both original replies on
October 12–13 and all three framework replies apply fall criteria early.
The original October 14 reasoning recognizes the summer window, but its JSON
still supplies a winter target of 1300 ft. That reply is internally inconsistent.

The saved evidence establishes incorrect date application. It does not establish
which retrieved sentence caused it. Differences in state also prevent a direct
same-state comparison of these later real replies.

## Proposed prompt change

The optional `seasonal_criteria_file` setting adds the current window from
[`seasonal_pool_criteria.json`](seasonal_pool_criteria.json). It provides bounds
and dates while leaving the release decision to the model. Summer retains
**no lower bound**; 1370 ft remains a ceiling, rather than a fixed target.

The separate [daily context preview](../../docs/_static/seasonal-context-preview.json)
shows the added text for these dates. It is a **proposed request**, not a
historical request or a new model reply. Original Anik and HydroReOpLLM use the
same text. Offline date and request tests can verify its construction; they
cannot prove that a real model will now apply every date correctly.

The [saved results](results.md) continue to show the previous prompts.
