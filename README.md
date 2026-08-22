# FortyDegrees ☕

A personal, Trade-Coffee-style specialty coffee recommender for Mumbai (400xxx).

Every two weeks, a scheduled [Codex cloud task](prompts/recommend.md) reads my taste
profile, rating history, and a catalog of Mumbai-deliverable specialty D2C roasters,
picks one coffee (plus two alternates), commits the cycle to `data/history.json`,
and emails me the recommendation with an order link and one-tap ★1–5 rating links.
A weekly [research task](prompts/research.md) grows and prunes the catalog.

The [Streamlit app](https://forty-degrees.streamlit.app) hosts the 7-question taste
quiz, the current pick, rating/reroll actions, and history.

- State: JSON files in `data/` (schemas in [AGENTS.md](AGENTS.md))
- Planning: the GitHub issue labeled `wayfinder:map` is the canonical decision log
- Secrets: `RESEND_API_KEY` (Codex environment), `GH_TOKEN` (Streamlit secrets) — never in the repo

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

Without a `GH_TOKEN` secret the app reads/writes `data/*.json` locally (dev mode).
