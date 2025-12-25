import json
import sys
import random
from typing import List, Tuple

# -------------------------
# 1. Basic card utilities (FROM TEMPLATE - SAME)
# -------------------------
RANKS = "23456789TJQKA"
RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}

def parse_card(card_str: str) -> Tuple[int, str]:
    return RANK_VALUE[card_str[0]], card_str[1]

def is_straight_3(rank_values: List[int]) -> Tuple[bool, int]:
    r = sorted(rank_values)
    if r[0] + 1 == r[1] and r[1] + 1 == r[2]:
        return True, r[2]
    if set(r) == {14, 2, 3}:
        return True, 3
    return False, 0

# --------------------------------------
# 2. Hand category evaluation (FROM TEMPLATE - SAME)
# --------------------------------------
def hand_category(hole: List[str], table: str) -> int:
    cards = hole + [table]
    rank_values, suits = zip(*[parse_card(c) for c in cards])
    flush = len(set(suits)) == 1
    counts = {}
    for v in rank_values:
        counts[v] = counts.get(v, 0) + 1
    straight, _ = is_straight_3(list(rank_values))
    if straight and flush: return 5
    if 3 in counts.values(): return 4
    if straight: return 3
    if flush: return 2
    if 2 in counts.values(): return 1
    return 0

# --------------------------------------
# 3. HELPER: Compare two hands (ADDED BY US)
# --------------------------------------
def compare_hands_internal(my_cards: List[str], table: str, opp_cards: List[str]) -> float:
    """
    Returns 1.0 if my_cards win, 0.0 if lose, 0.5 if tie.
    """
    my_rank = hand_category(my_cards, table)
    opp_rank = hand_category(opp_cards, table)
    
    if my_rank > opp_rank: return 1.0
    if opp_rank > my_rank: return 0.0
    
    # Tie-breaker logic (High card check)
    my_vals = sorted([parse_card(c)[0] for c in my_cards + [table]], reverse=True)
    opp_vals = sorted([parse_card(c)[0] for c in opp_cards + [table]], reverse=True)
    
    # Special A-2-3 handling
    if my_rank == 5 or my_rank == 3: 
        if set(my_vals) == {14, 3, 2}: my_vals = [3, 2, 1]
        if set(opp_vals) == {14, 3, 2}: opp_vals = [3, 2, 1]
    
    for m, o in zip(my_vals, opp_vals):
        if m > o: return 1.0
        if o > m: return 0.0
        
    return 0.5

# --------------------------------------
# 4. Main strategy function 
# --------------------------------------
def decide_action(state: dict) -> str:
    """
    Balanced Monte Carlo Strategy
    - Speed: 800 sims (Optimized for 40s Limit).
    - Logic: Uses Expected Value (EV) with a 'Trash Filter' to avoid bad hands.
    """
    try:
        hole = state.get("your_hole", [])
        table = state.get("table_card", "")
        stats = state.get("opponent_stats", {})
        
        # New: Read total rounds for dynamic adjustment context
        n_total_rounds = state.get("total_rounds", 1001)

        if not hole or not table:
            return "FOLD"

        # --- STEP 1: PRECISION MONTE CARLO ---
        # Build deck of unknown cards
        deck = []
        for r in "23456789TJQKA":
            for s in "HDSC":
                c = r+s
                if c not in hole and c != table:
                    deck.append(c)
        
        wins = 0
        sims = 800 
        
        for _ in range(sims):
            opp_hand = random.sample(deck, 2)
            wins += compare_hands_internal(hole, table, opp_hand)
        
        equity = wins / sims

        # --- STEP 2: STRATEGIC LOGIC ---
        
        # 1. TRASH FILTER
        if equity < 0.35:
            return "FOLD"

        # 2. ANALYZE OPPONENT
        n_fold = stats.get("fold", 0)
        n_actions = n_fold + stats.get("call", 0) + stats.get("raise", 0)
        
        fold_freq = 0.30
        if n_actions > 5:
            fold_freq = max(0.05, min(0.95, n_fold / n_actions))

        # 3. EV CALCULATION
        ev_fold = -1.0
        real_equity = equity 
        
        # EV Call
        ev_call_showdown = (real_equity * 2.0) + ((1 - real_equity) * -2.0)
        ev_call = (fold_freq * 2.0) + ((1 - fold_freq) * ev_call_showdown)

        # EV Raise
        ev_raise_showdown = (real_equity * 3.0) + ((1 - real_equity) * -3.0)
        ev_raise = (fold_freq * 3.0) + ((1 - fold_freq) * ev_raise_showdown)

        # 4. FINAL DECISION
        # We require a +0.10 profit margin to Raise (reduces variance).
        if ev_raise > ev_call + 0.10 and ev_raise > ev_fold:
            return "RAISE"
        
        if ev_call > ev_fold + 0.10:
            return "CALL"
            
        return "FOLD"

    except Exception:
        return "FOLD"

# -----------------------------
# 5. I/O glue (FROM TEMPLATE - SAME)
# -----------------------------
def main():
    raw = sys.stdin.read().strip()
    try:
        state = json.loads(raw) if raw else {}
    except Exception:
        state = {}

    action = decide_action(state)
    if action not in {"FOLD", "CALL", "RAISE"}:
        action = "CALL"

    sys.stdout.write(json.dumps({"action": action}))

if __name__ == "__main__":
    main()