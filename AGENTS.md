# AGENTS.md — FortyDegrees

FortyDegrees is a personal, Trade-Coffee-style specialty coffee recommender
for one Mumbai household: it curates a growing catalog of Indian D2C
roasters and, on its own schedule, picks and orders-links the next bag,
learning from ratings over time.

**Destination — the first fully-automatic cycle:** the weekly researcher and
the fortnightly recommender run unattended against this repo, entirely via
scheduled Codex cloud tasks, and produce one complete cycle — a catalog
update, a new pick emailed with working rate/reroll links, and (when
warranted) a corrections update — with zero human intervention between two
consecutive scheduled runs.

## Planning: the wayfinder map

The canonical planning artifact for this project is the GitHub issue on
this repo labeled **`wayfinder:map`**. It holds the standing decisions this
project runs on.

- Execution agents (the two scheduled prompts, and anyone doing code work
  here) must **not re-litigate decisions already closed on the map**.
  Treat a closed decision there as settled unless a human reopens it.
- Any **new** decision that affects behavior — a schema change, a new
  guardrail, a change to how matching or verification works — gets a
  **named ticket linked from the map before any code or prompt changes
  land**, not folded silently into an unrelated commit.

## Data schemas (canonical — use exactly these)

### `data/catalog.json`

```json
{"updated":"YYYY-MM-DD","roasters":[{"id":"kebab","name":"","city":"","website":"","products":[{"id":"kebab","name":"","roast":"light|light-medium|medium|medium-dark|dark","notes":["up-to-three"],"price_inr":0,"size_g":250,"order_url":"","verified":"YYYY-MM-DD"}]}]}
```

### `data/profile.json`

```json
{"created":"","brew_method":"french-press|pour-over|espresso|moka-pot|aeropress|south-indian-filter|drip|cold-brew","roast":"light|medium|dark","flavor_direction":"bright-fruity|chocolatey-sweet|nutty-balanced|bold-smoky","milk":"black|milk|sugar","format":"whole-bean|ground","chicory":"never|open|love","adventurousness":"classic|balanced|surprise","decaf":false}
```

### `data/history.json`

```json
{"cycles":[{"cycle":1,"date":"YYYY-MM-DD","pick":{"roaster_id":"","product_id":"","reasoning":""},"alternates":[{"roaster_id":"","product_id":"","reasoning":""},{"roaster_id":"","product_id":"","reasoning":""}],"rating":null,"rated_at":null,"rerolled":false,"reroll_history":[]}]}
```

### `data/corrections.json`

```json
{"<roaster_id>":{"stated":"medium","observed":"dark","evidence":"one line"}}
```

## Guardrails

- Scheduled runs (`prompts/recommend.md`, `prompts/research.md`) touch
  **only `data/*.json`** — never app code, never workflow/CI config, never
  these prompt files themselves.
- Keep all JSON valid at all times: no trailing commas, UTF-8 encoding.
- All dates are `YYYY-MM-DD`. All scheduling and "today" references are in
  **IST** (Asia/Kolkata).
- Secrets (`RESEND_API_KEY`, `GH_TOKEN`) live only in the Codex task
  environment / Streamlit secrets — **never** committed to this repo, never
  echoed into logs or commit messages.
- `APP_URL` constant: `https://forty-degrees.streamlit.app`
- User email: `harshad422@gmail.com`
