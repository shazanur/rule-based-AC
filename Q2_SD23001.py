#Q2
import json
from typing import List, Dict, Any, Tuple
import operator
import streamlit as st

# ----------------------------
# 1) Minimal rule engine
# ----------------------------
OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}

def evaluate_condition(facts: Dict[str, Any], cond: List[Any]) -> bool:
    """Evaluate a single condition: [field, op, value]."""
    if len(cond) != 3:
        return False
    field, op, value = cond
    if field not in facts or op not in OPS:
        return False
    try:
        return OPS[op](facts[field], value)
    except Exception:
        return False

def rule_matches(facts: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """All conditions must be true (AND)."""
    return all(evaluate_condition(facts, c) for c in rule.get("conditions", []))

def run_rules(
    facts: Dict[str, Any],
    rules: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns (best_action, fired_rules)
    - best_action: chosen by highest priority among fired rules (ties keep the first encountered)
    - fired_rules: list of rule dicts that matched
    """
    fired = [r for r in rules if rule_matches(facts, r)]
    if not fired:
        return ({"ac_mode": "REVIEW", "fan_speed": "-", "setpoint": None, "reason": "No rule matched"}, [])

    fired_sorted = sorted(fired, key=lambda r: r.get("priority", 0), reverse=True)
    best = fired_sorted[0].get(
        "action",
        {"ac_mode": "REVIEW", "fan_speed": "-", "setpoint": None, "reason": "No action"}
    )
    return best, fired_sorted


# ----------------------------
# 2) Load rules from JSON file
# ----------------------------
DEFAULT_RULES_FALLBACK: List[Dict[str, Any]] = []  # optional fallback if JSON fails

def load_rules_from_path(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Rules JSON must be a list of rules (JSON array).")
    return data


# ----------------------------
# 3) Streamlit UI (AC Controller Facts)
# ----------------------------
st.set_page_config(page_title="Rule-Based AC Controller", layout="wide")
st.title("Rule-Based Smart Home Air Conditioner Controller")
st.caption("Decides AC settings using predefined IF–THEN rules loaded from a JSON file.")

RULES_FILE_PATH = "json_q2.txt"

try:
    rules = load_rules_from_path(RULES_FILE_PATH)
    rules_source = f"Loaded from: {RULES_FILE_PATH}"
except Exception as e:
    st.error(f"Failed to load rules from JSON file. Using fallback rules. Details: {e}")
    rules = DEFAULT_RULES_FALLBACK
    rules_source = "Fallback rules (empty)"

with st.sidebar:
    st.header("Home Facts (Inputs)")
    temperature = st.number_input("temperature (°C)", min_value=-10.0, max_value=60.0, value=22.0, step=0.5)
    humidity = st.number_input("humidity (%)", min_value=0, max_value=100, value=46, step=1)

    occupancy = st.selectbox("occupancy", ["OCCUPIED", "EMPTY"], index=0)
    time_of_day = st.selectbox("time_of_day", ["MORNING", "AFTERNOON", "EVENING", "NIGHT"], index=3)

    windows_open = st.checkbox("windows_open", value=False)

    st.divider()
    st.caption(rules_source)

    run = st.button("Evaluate", type="primary")

facts = {
    "temperature": float(temperature),
    "humidity": int(humidity),
    "occupancy": str(occupancy),
    "time_of_day": str(time_of_day),
    "windows_open": bool(windows_open),
}

st.subheader("Home Facts")
st.json(facts)

st.subheader("Active Rules (from JSON file)")
with st.expander("Show rules", expanded=False):
    st.code(json.dumps(rules, indent=2), language="json")

st.divider()

def format_action(action: Dict[str, Any]) -> str:
    ac_mode = action.get("ac_mode", "-")
    fan_speed = action.get("fan_speed", "-")
    setpoint = action.get("setpoint", None)
    if setpoint is None:
        setpoint_str = "-"
    else:
        setpoint_str = f"{setpoint}°C"
    return f"AC Mode: {ac_mode} | Fan Speed: {fan_speed} | Setpoint: {setpoint_str}"

if run:
    action, fired = run_rules(facts, rules)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("AC Decision (Highest Priority Match)")
        decision_line = format_action(action)
        reason = action.get("reason", "-")

        st.success(decision_line)
        st.write(f"**Reason:** {reason}")

    with col2:
        st.subheader("Matched Rules (by priority)")
        if not fired:
            st.info("No rules matched.")
        else:
            for i, r in enumerate(fired, start=1):
                st.write(f"**{i}. {r.get('name','(unnamed)')}** | priority={r.get('priority',0)}")
                st.caption(f"Action: {r.get('action',{})}")
                with st.expander("Conditions"):
                    for cond in r.get("conditions", []):
                        st.code(str(cond))
else:
    st.info("Set the home facts and click **Evaluate**.")
