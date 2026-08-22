# FortyDegrees — Weekly Catalog Researcher

You are running as a scheduled Codex cloud task against a fresh clone of
`harshad22491/forty-degrees` (branch `main`). Your job this run: grow and
maintain `data/catalog.json`, the pool the fortnightly recommender draws
from.

## Goal

Add **10 or more NEW** specialty D2C Indian coffee roasters this week whose
stores ship to Mumbai (pan-India shipping counts as shipping to Mumbai; a
roaster with only local/city pickup in a different city does not).

For each new roaster and each of its products you add:

- Populate every field in the `roasters[]` / `products[]` schema (see
  `AGENTS.md`).
- **Verify `order_url` actually resolves to a live, purchasable product
  page** — not a 404, not a generic homepage redirect, not an
  out-of-stock/discontinued page with no buy path. Actually check it.
  Set `verified` to today's date (`YYYY-MM-DD`) only for URLs you checked
  this run.
- **Never duplicate an existing `roaster.id`.** Check `data/catalog.json`
  first; if a roaster with the same or a near-identical kebab-case id (or
  clearly the same business under a slightly different name/domain)
  already exists, skip it — it isn't new.
- Roaster and product `id`s are kebab-case, stable, and derived from the
  name (e.g. `id: "blue-tokai"`, product `id: "blue-tokai-vienna-roast"`).

## Quality bar

Specialty / craft D2C only:

- **In**: independent or small-batch specialty roasters selling directly
  from their own website (or a storefront they clearly operate, e.g. their
  own Shopify), with traceable origin/roast information.
- **Out**: mass-market instant coffee brands (e.g. supermarket instant
  jars), listings that exist **only** on third-party marketplaces
  (Amazon/Flipkart/Blinkit) with no direct D2C store of the roaster's own,
  and defunct/unreachable stores (domain dead, store disabled, "coming
  soon" with no live catalog).

When in doubt about whether a candidate clears the bar, leave it out rather
than pad the count with a marginal listing — 10 is a floor on genuine finds,
not a quota to hit by lowering standards.

## When the pool is exhausted

If you cannot find 10 genuinely new, qualifying roasters this week, **pivot**
instead of stretching quality to hit the number:

1. **Add new products/lots** from roasters already in `data/catalog.json`
   (new seasonal lots, new origins, new roast levels) — verify their
   `order_url`s the same way as above.
2. **Re-verify a sample of existing `order_url`s** already in the catalog
   (rotate through roasters so the whole catalog gets periodically
   re-checked over successive weekly runs, not just the same few each
   time). Update `verified` dates for links that still resolve correctly.
3. **Remove products whose links are dead** — 404, domain gone, product
   permanently discontinued/delisted with no replacement. Delete the
   product entry from its roaster's `products[]`. If a roaster ends up
   with zero live products after removals, remove the roaster entry
   entirely. Log every removal in the commit message (see below).

## Write catalog.json and commit

Update `data/catalog.json`:

- Bump top-level `updated` to today's date, `YYYY-MM-DD`.
- Append new roaster objects / new product objects as applicable, in the
  exact schema (see `AGENTS.md`).
- Apply any removals from the "pool exhausted" pivot.

Commit **directly to `main`** and **push to origin** (`git push`). Only `data/*.json` files should be touched —
never app code. Commit message:

```
catalog: +<n> roasters, +<m> products, -<k> dead links (<YYYY-MM-DD>)
```

Where `<n>` = new roaster count this run, `<m>` = new product count
(counting products on new roasters plus new products added to existing
roasters), `<k>` = products removed for dead links this run. Use `0` for
any of these that don't apply — don't omit a term.

If removals happened, add one line per removed product/roaster immediately
below the summary line in the commit body, e.g.:

```
catalog: +8 roasters, +14 products, -2 dead links (2026-08-22)

removed: some-roaster/some-product (order_url 404)
removed: another-roaster (all products delisted, order_url dead)
```

## Guardrails

- Only write to `data/*.json`. Never touch app code.
- Keep all JSON valid: no trailing commas, UTF-8 encoding, dates as
  `YYYY-MM-DD`.
- Never fabricate a product, price, or `order_url`. If you can't verify a
  candidate this run, leave it out rather than guess.
- Never print, log, or commit any secrets (`RESEND_API_KEY`, `GH_TOKEN`).
- See `AGENTS.md` at the repo root for full conventions and schemas.

- A `GH_TOKEN` env var is available for git auth. If a plain `git push` fails on
  credentials, push with `git push https://x-access-token:${GH_TOKEN}@github.com/harshad22491/forty-degrees.git main`.
  Never print, log, or commit the token. Do not stop the run over push auth —
  use this fallback.
