"""FortyDegrees: a personal coffee recommender for Mumbai."""
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st

from github_state import read_json, write_json

APP_URL = "https://forty-degrees.streamlit.app"
st.set_page_config(page_title="FortyDegrees", page_icon="☕", layout="centered")
st.markdown("""<style>
.chip{display:inline-block;background:#3c2415;color:#f4ede4;border-radius:1rem;padding:.2rem .7rem;font-size:.8rem}
.price{font-size:1.15rem;font-weight:650;font-variant-numeric:tabular-nums;margin:.8rem 0}
</style>""", unsafe_allow_html=True)


def safe_read(path, default, warn_missing=False):
    try:
        value = read_json(path)
    except Exception as exc:
        st.warning(f"Could not read {path} ({type(exc).__name__}); using safe defaults.")
        return default
    if value is None:
        if warn_missing:
            st.warning(f"{path} is not available yet; using safe defaults.")
        return default
    return value


def safe_write(path, value, message):
    try:
        write_json(path, value, message)
        return True
    except Exception as exc:
        st.error(f"Could not save {path} ({type(exc).__name__}). Please try again.")
        return False


profile = safe_read("data/profile.json", None)
history = safe_read("data/history.json", {"cycles": []}, True)
catalog = safe_read("data/catalog.json", {}, True)
if profile is not None and not isinstance(profile, dict):
    st.warning("The taste profile is malformed, so the quiz is shown instead.")
    profile = None
if not isinstance(history, dict):
    st.warning("History is malformed; recommendations are temporarily unavailable.")
    history = {"cycles": []}
if not isinstance(catalog, dict):
    st.warning("Catalog is malformed; details saved in history will still be shown.")
    catalog = {}
raw_cycles = history.get("cycles", [])
if not isinstance(raw_cycles, list):
    st.warning("History has no valid cycles list; treating it as empty.")
    raw_cycles = []
cycles = [item for item in raw_cycles if isinstance(item, dict)]
history["cycles"] = cycles


def objects(value):
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [{"id": key, **item} for key, item in value.items() if isinstance(item, dict)]
    return []


roasters = objects(catalog.get("roasters", []))
products = objects(catalog.get("products", []))
for roaster in roasters:
    for product in objects(roaster.get("products", [])):
        product.setdefault("roaster_id", roaster.get("id") or roaster.get("roaster_id"))
        products.append(product)
roaster_index = {str(x.get("id") or x.get("roaster_id")): x for x in roasters
                  if x.get("id") is not None or x.get("roaster_id") is not None}
product_index = {(str(x.get("roaster_id")), str(x.get("id") or x.get("product_id"))): x for x in products
                 if x.get("id") is not None or x.get("product_id") is not None}


def first(*values, fallback=""):
    return next((value for value in values if value not in (None, "")), fallback)


def details(pick):
    pick = pick if isinstance(pick, dict) else {}
    product = product_index.get((str(pick.get("roaster_id")), str(pick.get("product_id"))), {})
    roaster_id = first(pick.get("roaster_id"), product.get("roaster_id"))
    roaster = roaster_index.get(str(roaster_id), {})
    notes = first(product.get("tasting_notes"), product.get("notes"),
                  pick.get("tasting_notes"), pick.get("notes"), fallback="Not listed yet")
    if isinstance(notes, list):
        notes = ", ".join(map(str, notes))
    return {
        "name": str(first(product.get("name"), pick.get("product_name"), pick.get("name"),
                          pick.get("product_id"), fallback="Coffee pick")),
        "roaster": str(first(roaster.get("name"), product.get("roaster_name"),
                             pick.get("roaster_name"), roaster_id, fallback="Roaster not listed")),
        "city": str(first(roaster.get("city"), product.get("city"), pick.get("roaster_city"), pick.get("city"))),
        "roast": str(first(product.get("roast_level"), product.get("roast"),
                           pick.get("roast_level"), pick.get("roast"), fallback="Roast not listed")),
        "notes": str(notes), "price": first(product.get("price_inr"), pick.get("price_inr")),
        "size": first(product.get("size_g"), pick.get("size_g"), fallback=250),
        "url": str(first(product.get("order_url"), pick.get("order_url"))),
        "why": str(first(pick.get("reasoning"), fallback="More match details arrive with the cycle.")),
    }


def price(value, size):
    try:
        amount = float(value) * 250 / float(size)
        return f"₹{amount:,.0f}/250g" if amount.is_integer() else f"₹{amount:,.2f}/250g"
    except (TypeError, ValueError, ZeroDivisionError):
        return "Price not listed"


def today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()


def cycle_num(cycle):
    try:
        return int(cycle.get("cycle"))
    except (TypeError, ValueError):
        return -1


def find_cycle(number):
    return next((cycle for cycle in cycles if str(cycle.get("cycle")) == str(number)), None)


def rate_cycle(cycle, rating):
    cycle["rating"], cycle["rated_at"] = rating, today()
    number = cycle.get("cycle")
    return safe_write("data/history.json", history, f"rate cycle {number}: {rating} stars")


def reroll_cycle(cycle):
    alternates = cycle.get("alternates", [])
    if not isinstance(alternates, list) or not alternates or not isinstance(alternates[0], dict):
        st.warning("This cycle has no alternate recommendation available.")
        return None
    prior = cycle.get("reroll_history", [])
    prior = prior if isinstance(prior, list) else []
    if isinstance(cycle.get("pick"), dict):
        prior.append(cycle["pick"])
    cycle["reroll_history"], cycle["pick"] = prior, alternates.pop(0)
    cycle["alternates"], cycle["rerolled"] = alternates, True
    if safe_write("data/history.json", history, f"reroll cycle {cycle.get('cycle')}"):
        return cycle["pick"]
    return None


def query_value(key):
    value = st.query_params.get(key)
    return value[0] if isinstance(value, list) and value else value


def query_action():
    rate, reroll = query_value("rate"), query_value("reroll")
    if rate is None and reroll is None:
        return False
    st.title("FortyDegrees")
    cycle = find_cycle(query_value("cycle"))
    if cycle is None:
        st.warning("That recommendation cycle could not be found.")
        return True
    coffee = details(cycle.get("pick"))["name"]
    if rate is not None:
        try:
            rating = int(rate)
        except (TypeError, ValueError):
            rating = 0
        if rating not in range(1, 6):
            st.warning("Ratings must be from 1 to 5 stars.")
        else:
            st.write(f"Rate **{coffee}** from cycle {cycle.get('cycle')}.")
            if st.button(f"Save rating: {rating}★", type="primary") and rate_cycle(cycle, rating):
                st.query_params.clear()
                st.success(f"Saved {rating}★ for {coffee}.")
        return True
    if str(reroll) != "1":
        st.warning("That reroll link is not valid.")
        return True
    st.write(f"Replace **{coffee}** with the first alternate?")
    if st.button("Confirm recommendation change", type="primary"):
        new_pick = reroll_cycle(cycle)
        if new_pick:
            st.query_params.clear()
            st.success(f"Your new pick is **{details(new_pick)['name']}**.")
    return True


if query_action():
    st.stop()


QUESTIONS = [
    ("brew_method", "How do you brew?", ["french-press", "pour-over", "espresso", "moka-pot", "aeropress", "south-indian-filter", "drip", "cold-brew"]),
    ("roast", "Which roast do you prefer?", ["light", "medium", "dark"]),
    ("flavor_direction", "Which flavor direction sounds best?", ["bright-fruity", "chocolatey-sweet", "nutty-balanced", "bold-smoky"]),
    ("milk", "How do you drink it?", ["black", "milk", "sugar"]),
    ("format", "What format do you buy?", ["whole-bean", "ground"]),
    ("chicory", "How do you feel about chicory / filter kaapi?", ["never", "open", "love"]),
    ("adventurousness", "How adventurous should your picks be?", ["classic", "balanced", "surprise"]),
]
LABELS = {
    "bright-fruity": "Bright & fruity", "chocolatey-sweet": "Chocolatey & sweet",
    "nutty-balanced": "Nutty & balanced", "bold-smoky": "Bold & smoky",
    "south-indian-filter": "South Indian filter", "aeropress": "AeroPress",
    "open": "Open to it", "love": "Love it", "surprise": "Surprise me",
}


def choice_label(value):
    return LABELS.get(value, value.replace("-", " ").capitalize())


def reset_quiz():
    for key in list(st.session_state):
        if key.startswith("quiz_"):
            del st.session_state[key]


def show_quiz():
    st.title("FortyDegrees")
    st.caption("Seven quick questions for a better Mumbai coffee pick.")
    step = st.session_state.setdefault("quiz_step", 0)
    answers = st.session_state.setdefault("quiz_answers", {})
    st.progress((step + 1) / 8)
    if step < 7:
        field, question, options = QUESTIONS[step]
        saved = answers.get(field)
        index = options.index(saved) if saved in options else 0
        st.caption(f"Question {step + 1} of 7")
        answers[field] = st.radio(question, options, index=index, format_func=choice_label,
                                  key=f"quiz_choice_{step}")
        back, forward = st.columns(2)
        if back.button("Back", disabled=step == 0, use_container_width=True):
            st.session_state.quiz_step -= 1
            st.rerun()
        if forward.button("Next", type="primary", use_container_width=True):
            st.session_state.quiz_step += 1
            st.rerun()
        return
    st.subheader("One last preference")
    decaf = st.toggle("Decaf only", value=False, key="quiz_decaf")
    back, save = st.columns(2)
    if back.button("Back", use_container_width=True):
        st.session_state.quiz_step -= 1
        st.rerun()
    if save.button("Save taste profile", type="primary", use_container_width=True):
        new_profile = {"created": today(), **answers, "decaf": bool(decaf)}
        if safe_write("data/profile.json", new_profile, "create taste profile"):
            reset_quiz()
            st.rerun()


def show_sidebar():
    st.sidebar.header("Your profile")
    decaf = st.sidebar.toggle("Decaf only", value=bool(profile.get("decaf", False)))
    if decaf != bool(profile.get("decaf", False)):
        updated = {**profile, "decaf": decaf}
        if safe_write("data/profile.json", updated, "update decaf preference"):
            profile.update(updated)
            st.sidebar.success("Preference saved.")
    if st.sidebar.button("Retake quiz"):
        st.session_state.confirm_retake = True
    if st.session_state.get("confirm_retake"):
        st.sidebar.warning("This clears your current taste profile.")
        yes, no = st.sidebar.columns(2)
        if yes.button("Confirm", type="primary", use_container_width=True):
            if safe_write("data/profile.json", {}, "clear taste profile"):
                reset_quiz()
                st.session_state.confirm_retake = False
                st.rerun()
        if no.button("Cancel", use_container_width=True):
            st.session_state.confirm_retake = False
            st.rerun()
    st.sidebar.divider()
    st.sidebar.caption("FortyDegrees is your personal Mumbai coffee picker, refreshed by a scheduled recommendation run.")


def show_pick(cycle):
    item = details(cycle.get("pick"))
    st.subheader("Current pick")
    st.header(item["name"])
    st.caption(item["roaster"] + (f" · {item['city']}" if item["city"] else ""))
    st.markdown(f'<span class="chip">{escape(item["roast"])}</span>'
                f'<div class="price">{escape(price(item["price"], item["size"]))}</div>', unsafe_allow_html=True)
    st.markdown("**Tasting notes**")
    st.write(item["notes"])
    st.write(item["why"])
    if item["url"].startswith(("https://", "http://")):
        st.link_button("Order now →", item["url"], type="primary")
    else:
        st.caption("Ordering link not available yet.")
    saved = cycle.get("rating")
    try:
        saved = int(saved)
    except (TypeError, ValueError):
        saved = None
    if saved:
        st.caption(f"Your current rating: {saved}★")
    left, right = st.columns(2)
    with left:
        feedback = st.feedback("stars", key=f"stars_{cycle.get('cycle')}")
        if feedback is not None and feedback + 1 != saved and rate_cycle(cycle, feedback + 1):
            st.success("Rating saved.")
    with right:
        available = isinstance(cycle.get("alternates"), list) and bool(cycle["alternates"])
        if st.button("Recommend another", disabled=not available, use_container_width=True):
            st.query_params["reroll"], st.query_params["cycle"] = "1", str(cycle.get("cycle"))
            st.rerun()


def show_history():
    st.divider()
    st.subheader("History")
    if not cycles:
        st.caption("No recommendation cycles yet.")
        return
    rows = []
    for cycle in sorted(cycles, key=cycle_num, reverse=True):
        item, rating = details(cycle.get("pick")), cycle.get("rating")
        rows.append({"Cycle": cycle.get("cycle", "—"), "Date": cycle.get("date", "—"),
                     "Coffee": item["name"], "Roaster": item["roaster"],
                     "Rating": f"{rating}★" if rating not in (None, "") else "—",
                     "Rerolled": bool(cycle.get("rerolled"))})
    st.dataframe(rows, hide_index=True, use_container_width=True)


if not profile:
    show_quiz()
else:
    show_sidebar()
    st.title("FortyDegrees")
    st.caption("Your personal coffee recommendation for Mumbai.")
    if cycles:
        show_pick(max(cycles, key=cycle_num))
    else:
        st.info("Your first recommendation lands with the next scheduled run.")
        left, right = st.columns(2)
        left.metric("Roasters in catalog", len(roasters))
        right.metric("Products in catalog", len(products))
    show_history()
