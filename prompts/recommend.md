# FortyDegrees — Fortnightly Recommender

You are running as a scheduled Codex cloud task against a fresh clone of
`harshad22491/forty-degrees` (branch `main`). Your job this run: read the
household's coffee profile and history, pick the next bag, write it to
history, and email it.

## 0. Preconditions

1. Read `data/profile.json`.
   - If the file is missing, unreadable, or an empty object `{}` (no
     `brew_method`/`roast`/etc. set) → **do nothing and exit**. Do not
     commit, do not send email. A profile-less household has nothing to
     recommend against.
2. Read `data/history.json`, `data/catalog.json`, and `data/corrections.json`
   (treat a missing `corrections.json` as `{}`).

## 1. Matching — pure LLM judgment, no scoring formula

There is no numeric scoring function here. Reason directly over the full
context:

- The complete `profile.json` (brew method, roast, flavor direction, milk,
  format, chicory stance, adventurousness, decaf).
- **Every** past cycle in `history.json` — picks, alternates, ratings, and
  reroll history. Read all of it, not just the last cycle.
- `data/corrections.json` — per-roaster corrections where the roaster's
  stated roast label has been observed to run lighter/darker than labeled.
  When judging whether a product matches the profile's `roast` preference,
  apply the correction instead of trusting the roaster's own label.

Hard rules:

- **Never re-recommend** a `roaster_id`/`product_id` pair that was rated
  `< 4` in any past cycle.
- A **reroll** (`rerolled: true` / non-empty `reroll_history`) on a past
  cycle counts as a **mild negative signal** for the product that was
  rerolled away from — treat it like a soft "this wasn't it," even without
  a numeric rating.
- Respect `profile.decaf`: if `true`, only consider decaf products; if the
  catalog has no decaf marking, use product `notes`/`name` to judge and
  when genuinely unsure, say so in the reasoning rather than guessing.
- `profile.adventurousness` governs how far off-center the pick may be:
  - `classic` → stay close to previously well-rated (≥4) picks and the
    stated flavor direction.
  - `balanced` → mostly on-profile, one dimension of moderate stretch is
    fine (e.g. new roaster, same flavor direction).
  - `surprise` → actively favor a roaster or flavor note combination not
    yet tried, as long as it doesn't violate a hard rule above.
- No budget ceiling exists. Never filter or penalize by `price_inr` — but
  **always state the price** in the reasoning and in the email.

## 2. Output: one pick, two ranked alternates

Select:

- **1 pick** — the primary recommendation.
- **2 alternates**, ranked (alternate 1 = stronger runner-up).

For the pick and each alternate, write 1–3 sentences of "why this matches
you" reasoning that is **grounded in specifics**: reference the actual
profile fields and/or actual past ratings/rerolls that justify the choice.
Generic praise ("a crowd-pleaser!") is not acceptable — every reasoning
sentence should be traceable to something in `profile.json`, `history.json`,
or `corrections.json`.

## 3. Low-rating follow-up (before writing history)

Check the most recently rated cycle in `history.json` (the latest cycle with
`rating` not null):

- If that `rating <= 2`, reason about whether a **roast mismatch** is the
  likely cause (e.g. profile says `medium`, product/roaster is `dark` or
  `light`, or a `corrections.json` entry suggests the roaster's stated
  label doesn't match reality).
- If roast mismatch looks like the likely cause, **add or update** the
  relevant entry in `data/corrections.json` in the same commit as the new
  history entry, e.g.:

  ```json
  {
    "roaster-id": {
      "stated": "medium",
      "observed": "dark",
      "evidence": "cycle 3 rated 2/5, notes described as 'too smoky/burnt' for a stated medium roast"
    }
  }
  ```

  Keep `evidence` to one line. Only touch the roaster(s) implicated by that
  low rating — do not rewrite unrelated correction entries.

## 4. Write history.json and commit

Append a new object to `history.json`'s `cycles` array:

- `cycle`: previous max `cycle` + 1 (or `1` if `cycles` is empty).
- `date`: today's date, `YYYY-MM-DD`, IST.
- `pick`: `{roaster_id, product_id, reasoning}`.
- `alternates`: the two ranked alternate objects, same shape.
- `rating`: `null`.
- `rated_at`: `null`.
- `rerolled`: `false`.
- `reroll_history`: `[]`.

Commit **directly to `main`** and **push to origin** (`git push origin HEAD:main`; if credentials fail use the GH_TOKEN fallback below). Only `data/*.json` files should be touched
(plus `corrections.json` if step 3 applies). Commit message:

```
cycle <N>: <product name>
```

## 5. "Rate your last bag" reminder

If the **previous** cycle (the one before the new cycle you just wrote) has
`rating: null` (i.e. it was never rated), the email must include a gentle
reminder to rate it — see the template below.

## 6. Send the email — Resend HTTP API

Send via `POST https://api.resend.com/emails` with header
`Authorization: Bearer $RESEND_API_KEY` (env var; never hardcode or print
the key).

- `from`: `"FortyDegrees <onboarding@resend.dev>"`
- `to`: `"harshad422@gmail.com"`
- `subject`: `"Your next coffee: <product> from <roaster>"`
- `html`: the fully-rendered template below.

### Email template (fill placeholders, keep HTML self-contained / inline styles only)

```html
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#f4ede4;font-family:Georgia,'Times New Roman',serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4ede4;padding:32px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(60,40,20,0.08);">
            <tr>
              <td style="background-color:#3c2415;padding:24px 32px;">
                <span style="color:#f4ede4;font-size:22px;font-weight:bold;letter-spacing:0.5px;">FortyDegrees</span>
                <div style="color:#c9a876;font-size:13px;margin-top:4px;">Your fortnightly coffee, chosen for you</div>
              </td>
            </tr>

            <!-- REMINDER BLOCK: include this <tr> only if step 5 applies, omit entirely otherwise -->
            <tr>
              <td style="padding:20px 32px 0 32px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#fbf3e7;border-left:4px solid #c9a876;border-radius:4px;">
                  <tr>
                    <td style="padding:14px 18px;color:#5c4530;font-size:14px;line-height:1.5;">
                      Quick nudge — you haven't rated your last bag yet (cycle {{PREV_CYCLE}}).
                      <a href="{{APP_URL}}" style="color:#8b5a2b;font-weight:bold;">Rate it in 5 seconds</a>
                      so future picks stay sharp.
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <!-- END REMINDER BLOCK -->

            <tr>
              <td style="padding:28px 32px 8px 32px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8dcc8;border-radius:10px;">
                  <tr>
                    <td style="padding:22px 24px;">
                      <div style="color:#8b5a2b;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Cycle {{CYCLE}} pick</div>
                      <div style="color:#2b1a0f;font-size:22px;font-weight:bold;">{{PRODUCT_NAME}}</div>
                      <div style="color:#6b5644;font-size:15px;margin-top:2px;">{{ROASTER_NAME}} &middot; {{ROASTER_CITY}}</div>
                      <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:14px;">
                        <tr>
                          <td style="background-color:#3c2415;color:#f4ede4;font-size:12px;padding:4px 10px;border-radius:12px;">{{ROAST_LEVEL}}</td>
                          <td style="width:8px;"></td>
                          <td style="background-color:#eee3d0;color:#5c4530;font-size:12px;padding:4px 10px;border-radius:12px;">₹{{PRICE_INR}} / {{SIZE_G}}g</td>
                        </tr>
                      </table>
                      <div style="color:#6b5644;font-size:14px;margin-top:14px;">Notes: {{TASTING_NOTES}}</div>
                      <p style="color:#3c2415;font-size:15px;line-height:1.6;margin-top:16px;">{{PICK_REASONING}}</p>
                      <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:18px;">
                        <tr>
                          <td style="background-color:#c9a876;border-radius:6px;">
                            <a href="{{ORDER_URL}}" style="display:inline-block;padding:12px 28px;color:#2b1a0f;font-weight:bold;font-size:15px;text-decoration:none;">ORDER NOW</a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:20px 32px 4px 32px;color:#5c4530;font-size:13px;">How was it? Rate this pick:</td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px 32px;">
                <a href="{{APP_URL}}/?rate=1&cycle={{CYCLE}}" style="color:#c9a876;text-decoration:none;font-size:20px;margin-right:6px;">&#9733;1</a>
                <a href="{{APP_URL}}/?rate=2&cycle={{CYCLE}}" style="color:#c9a876;text-decoration:none;font-size:20px;margin-right:6px;">&#9733;2</a>
                <a href="{{APP_URL}}/?rate=3&cycle={{CYCLE}}" style="color:#c9a876;text-decoration:none;font-size:20px;margin-right:6px;">&#9733;3</a>
                <a href="{{APP_URL}}/?rate=4&cycle={{CYCLE}}" style="color:#c9a876;text-decoration:none;font-size:20px;margin-right:6px;">&#9733;4</a>
                <a href="{{APP_URL}}/?rate=5&cycle={{CYCLE}}" style="color:#c9a876;text-decoration:none;font-size:20px;">&#9733;5</a>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 24px 32px;">
                <a href="{{APP_URL}}/?reroll=1&cycle={{CYCLE}}" style="color:#8b5a2b;font-size:13px;">Recommend me another &rarr;</a>
              </td>
            </tr>

            <tr>
              <td style="padding:8px 32px 28px 32px;border-top:1px solid #e8dcc8;">
                <div style="color:#8b5a2b;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin:18px 0 10px 0;">If not this one</div>

                <div style="color:#2b1a0f;font-size:15px;font-weight:bold;">1. {{ALT1_PRODUCT_NAME}} — {{ALT1_ROASTER_NAME}}</div>
                <div style="color:#6b5644;font-size:13px;margin:2px 0 6px 0;">{{ALT1_ROAST_LEVEL}} &middot; ₹{{ALT1_PRICE_INR}}/{{ALT1_SIZE_G}}g &middot; <a href="{{ALT1_ORDER_URL}}" style="color:#8b5a2b;">order</a></div>
                <p style="color:#3c2415;font-size:14px;line-height:1.5;margin:0 0 16px 0;">{{ALT1_REASONING}}</p>

                <div style="color:#2b1a0f;font-size:15px;font-weight:bold;">2. {{ALT2_PRODUCT_NAME}} — {{ALT2_ROASTER_NAME}}</div>
                <div style="color:#6b5644;font-size:13px;margin:2px 0 6px 0;">{{ALT2_ROAST_LEVEL}} &middot; ₹{{ALT2_PRICE_INR}}/{{ALT2_SIZE_G}}g &middot; <a href="{{ALT2_ORDER_URL}}" style="color:#8b5a2b;">order</a></div>
                <p style="color:#3c2415;font-size:14px;line-height:1.5;margin:0;">{{ALT2_REASONING}}</p>
              </td>
            </tr>

            <tr>
              <td style="background-color:#f4ede4;padding:16px 32px;color:#a08c74;font-size:11px;text-align:center;">
                FortyDegrees &middot; a personal coffee picker, run just for you.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
```

`{{APP_URL}}` is `https://harshad22491-forty-degrees-app-jmcqok.streamlit.app`. Substitute every
`{{...}}` placeholder with real values before sending; do not leave any
placeholder unfilled. Omit the reminder `<tr>` block entirely when step 5
does not apply (do not send it empty/hidden — remove the markup).

## Guardrails

- Only write to `data/*.json`. Never touch app code.
- Keep all JSON valid: no trailing commas, UTF-8 encoding, dates as
  `YYYY-MM-DD`.
- Never print, log, or commit `RESEND_API_KEY` or `GH_TOKEN`.
- See `AGENTS.md` at the repo root for full conventions and schemas.

- A `GH_TOKEN` env var is available for git auth. If a plain `git push` fails on
  credentials, push with `git push https://x-access-token:${GH_TOKEN}@github.com/harshad22491/forty-degrees.git HEAD:main`.
  Never print, log, or commit the token. Do not stop the run over push auth —
  use this fallback.
