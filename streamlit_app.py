import streamlit as st
import plotly.graph_objects as go
from copy import deepcopy

st.set_page_config(
    page_title="💰 Money Creation Game",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS (Aynı bıraktım, Syne font ve custom bileşenler) ───────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Syne', sans-serif !important; }
.sb-metric { background: white; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 8px; padding: 10px 12px; margin-bottom: 7px; }
.sb-metric-label { font-size: 10px; color: #6b6b6b; text-transform: uppercase; }
.sb-metric-val { font-size: 22px; font-weight: 700; color: #1a1a1a; }
.step-header-card { background: #EEF2FF; border: 1px solid #C7D2FE; border-radius: 12px; padding: 16px 20px; margin-bottom: 10px; }
.flow-strip { background: #f7f7f5; border: 0.5px solid rgba(0,0,0,0.10); border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; }
.bsheet { border: 0.5px solid rgba(0,0,0,0.12); border-radius: 8px; overflow: hidden; margin-bottom: 8px; }
.bsheet.active { border: 1.5px solid #378ADD; }
.insight-bar { background: #EAF3DE; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #3B6D11; margin-bottom: 10px; }
.tag { display:inline-block; font-size:11px; font-weight:700; padding:3px 10px; border-radius:20px; }
.tag-green { background:#EAF3DE; color:#3B6D11; }
.tag-blue { background:#E6F1FB; color:#185FA5; }
.tag-red { background:#FCEBEB; color:#A32D2D; }
</style>
""", unsafe_allow_html=True)

# ─── SCENARIOS ────────────────────────────────────────────────────────────────
SCENARIOS = [
    {
        "id": 1, "emoji": "✨", "title": "Bank X Creates Money", "short": "Bank X grants Customer A a loan.",
        "insight": "Banks create money when they make loans. This is endogenous money.",
        "tag": "💚 Money Created", "tag_type": "green", "involved": ["Xbank","CustomerA"],
        "transactions": [("Xbank","debit","Credits",100),("Xbank","credit","CustomerADep",100),("CustomerA","debit","Deposits",100),("CustomerA","credit","Credits",100)],
        "flow_label": "loan creation"
    },
    {
        "id": 2, "emoji": "🏛️", "title": "Central Bank Provides Reserves", "short": "CB lends reserves to Bank X and Y.",
        "insight": "Reserves settle inter-bank payments and stay in the CB ledger.",
        "tag": "➡️ No Change in M1", "tag_type": "blue", "involved": ["Xbank","Ybank","CentralBank"],
        "transactions": [("Xbank","debit","Reserves",100),("Xbank","credit","DueCB",100),("Ybank","debit","Reserves",100),("Ybank","credit","DueCB",100),("CentralBank","debit","CreditsToBanks",200),("CentralBank","credit","Reserves",200)],
        "flow_label": "reserve injection"
    },
    {
        "id": 3, "emoji": "💳", "title": "Bank Y Creates a Loan", "short": "Bank Y grants Customer C a loan.",
        "insight": "Every bank creates money independently through bookkeeping.",
        "tag": "💚 Money Created", "tag_type": "green", "involved": ["Ybank","CustomerC"],
        "transactions": [("Ybank","debit","Credits",100),("Ybank","credit","CustomerCDep",100),("CustomerC","debit","Deposits",100),("CustomerC","credit","Credits",100)],
        "flow_label": "loan creation"
    },
    {
        "id": 4, "emoji": "💳", "title": "Bank X Creates a Loan", "short": "Bank X grants Customer B a loan.",
        "insight": "The money supply grows as banks manufacture new purchasing power.",
        "tag": "💚 Money Created", "tag_type": "green", "involved": ["Xbank","CustomerB"],
        "transactions": [("Xbank","debit","Credits",100),("Xbank","credit","CustomerBDep",100),("CustomerB","debit","Deposits",100),("CustomerB","credit","Credits",100)],
        "flow_label": "loan creation"
    },
    {
        "id": 5, "emoji": "📉", "title": "Customer B Repays Loan", "short": "Customer B repays part of the loan.",
        "insight": "Loan repayments destroy money. It disappears from the balance sheet.",
        "tag": "🔴 Money Destroyed", "tag_type": "red", "involved": ["Xbank","CustomerB"],
        "transactions": [("Xbank","debit","CustomerBDep",70),("Xbank","credit","Credits",70),("CustomerB","debit","Credits",70),("CustomerB","credit","Deposits",70)],
        "flow_label": "money destruction"
    },
    {
        "id": 6, "emoji": "💸", "title": "Customer A Pays B (Same Bank)", "short": "Internal transfer at Bank X.",
        "insight": "Same-bank payments don't require reserves. Pure bookkeeping.",
        "tag": "➡️ Transfer Only", "tag_type": "blue", "involved": ["Xbank","CustomerA","CustomerB"],
        "transactions": [("Xbank","debit","CustomerADep",50),("Xbank","credit","CustomerBDep",50),("CustomerA","debit","NetWorth",50),("CustomerA","credit","Deposits",50),("CustomerB","debit","Deposits",50),("CustomerB","credit","NetWorth",50)],
        "flow_label": "internal transfer"
    },
    {
        "id": 7, "emoji": "🔄", "title": "Customer C Pays A (Cross-Bank)", "short": "Reserves must move to settle this.",
        "insight": "Cross-bank payments require central bank reserves to settle.",
        "tag": "➡️ Transfer Only", "tag_type": "blue", "involved": ["Xbank","Ybank","CustomerA","CustomerC"],
        "transactions": [("Xbank","debit","Reserves",50),("Xbank","credit","CustomerADep",50),("Ybank","debit","CustomerCDep",50),("Ybank","credit","Reserves",50),("CustomerA","debit","Deposits",50),("CustomerA","credit","NetWorth",50),("CustomerC","debit","NetWorth",50),("CustomerC","credit","Deposits",50)],
        "flow_label": "reserve settlement"
    },
    {
        "id": 8, "emoji": "💵", "title": "Banks Withdraw Cash", "short": "Banks convert reserves to physical cash.",
        "insight": "Cash and reserves are both central bank money formats.",
        "tag": "➡️ Form Change Only", "tag_type": "blue", "involved": ["Xbank","Ybank","CentralBank"],
        "transactions": [("Xbank","debit","Cash",20),("Xbank","credit","Reserves",20),("Ybank","debit","Cash",20),("Ybank","credit","Reserves",20),("CentralBank","debit","Reserves",40),("CentralBank","credit","Cash",40)],
        "flow_label": "cash withdrawal"
    },
    {
        "id": 9, "emoji": "🏧", "title": "Customer A Withdraws Cash", "short": "Bank money becomes central bank cash.",
        "insight": "Total money supply stays the same; only the format changes.",
        "tag": "➡️ Form Change Only", "tag_type": "blue", "involved": ["Xbank","CustomerA"],
        "transactions": [("Xbank","debit","CustomerADep",20),("Xbank","credit","Cash",20),("CustomerA","debit","Cash",20),("CustomerA","credit","Deposits",20)],
        "flow_label": "cash withdrawal"
    }
]

# ─── ENGINE ───────────────────────────────────────────────────────────────────
ENTITY_DEFS = {
    "Xbank": {"label":"Bank X", "assets":{"Cash":0,"Reserves":0,"Credits":0}, "liabilities":{"CustomerADep":0,"CustomerBDep":0,"DueCB":0}},
    "Ybank": {"label":"Bank Y", "assets":{"Cash":0,"Reserves":0,"Credits":0}, "liabilities":{"CustomerCDep":0,"DueCB":0}},
    "CentralBank": {"label":"Central Bank", "assets":{"CreditsToBanks":0}, "liabilities":{"Reserves":0,"Cash":0}},
    "CustomerA": {"label":"Customer A", "assets":{"Cash":0,"Deposits":0}, "liabilities":{"Credits":0,"NetWorth":0}},
    "CustomerB": {"label":"Customer B", "assets":{"Deposits":0}, "liabilities":{"Credits":0,"NetWorth":0}},
    "CustomerC": {"label":"Customer C", "assets":{"Deposits":0}, "liabilities":{"Credits":0,"NetWorth":0}},
}

def init_state(): return {k: {"assets": dict(v["assets"]), "liabilities": dict(v["liabilities"])} for k, v in ENTITY_DEFS.items()}

def apply_tx(state, txs, amount_override):
    s = deepcopy(state)
    for entity, side, account, base_amt in txs:
        # Step 2 and 8 have specific math (totals), handled via amount_override logic
        amt = amount_override
        if entity == "CentralBank":
            if "Reserves" in account or "CreditsToBanks" in account:
                amt = amount_override * 2 # Two banks involved
        
        e = s[entity]
        if side == "debit":
            if account in e["assets"]: e["assets"][account] += amt
            elif account in e["liabilities"]: e["liabilities"][account] -= amt
        else:
            if account in e["assets"]: e["assets"][account] -= amt
            elif account in e["liabilities"]: e["liabilities"][account] += amt
    return s

def compute_ms(state):
    bank = sum(state["Xbank"]["liabilities"].get(k,0) + state["Ybank"]["liabilities"].get(k,0) for k in ["CustomerADep","CustomerBDep","CustomerCDep"])
    cash = sum(state[e]["assets"].get("Cash",0) for e in ["CustomerA","CustomerB","CustomerC","Xbank","Ybank"])
    return bank, cash, bank + cash

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 0
    st.session_state.live_state = init_state()
    st.session_state.history = [deepcopy(st.session_state.live_state)]
    st.session_state.ms_history = [{"label": "Start", "bank": 0, "cash": 0, "total": 0}]

def go_prev():
    if st.session_state.step > 0:
        st.session_state.step -= 1
        st.session_state.live_state = deepcopy(st.session_state.history[st.session_state.step])

def go_next(amt):
    if st.session_state.step < 9:
        sc = SCENARIOS[st.session_state.step]
        new_state = apply_tx(st.session_state.live_state, sc["transactions"], amt)
        st.session_state.live_state = new_state
        st.session_state.step += 1
        st.session_state.history.append(deepcopy(new_state))
        bm, cm, tot = compute_ms(new_state)
        st.session_state.ms_history.append({"label": f"Step {st.session_state.step}", "bank": bm, "cash": cm, "total": tot})

def reset():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# ─── MAIN UI ──────────────────────────────────────────────────────────────────
current_step = st.session_state.step
state = st.session_state.live_state

with st.sidebar:
    st.markdown("### 💰 Money Simulator")
    st.info(f"Step: {current_step} / 9")
    ms = st.session_state.ms_history[current_step]
    st.metric("Total Money Supply (M1)", f"${ms['total']}")
    st.metric("Bank Deposits", f"${ms['bank']}")
    st.metric("Physical Cash", f"${ms['cash']}")
    if st.button("↺ Reset All"): reset()

# Miktar Seçici
selected_amount = 100
if current_step < 9:
    sc = SCENARIOS[current_step]
    if current_step in [0, 2, 3]: # Creation
        opts = [100, 200, 300, 400]; lbl = "Select amount to CREATE:"
    elif current_step == 1: # Reserves
        opts = [100, 200, 300, 400]; lbl = "Select RESERVES to inject:"
    elif current_step in [5, 6]: # Transfers
        opts = [20, 25, 30, 50]; lbl = "Select TRANSFER amount:"
    elif current_step in [7, 8]: # Cash
        opts = [10, 20, 30, 40]; lbl = "Select CASH amount:"
    elif current_step == 4: # Repay
        opts = [5, 10, 15, 20]; lbl = "Select REPAYMENT amount:"
    
    st.markdown(f"**{lbl}**")
    selected_amount = st.select_slider("", options=opts, value=opts[0], label_visibility="collapsed")

# Header Logic
if current_step == 0:
    h_title, h_desc, h_tag = "🚀 Start the System", "Everything is at zero. Pick an amount to create the first loan.", "System Idle"
    involved = []
else:
    prev_sc = SCENARIOS[current_step-1]
    h_title, h_desc, h_tag = f"{prev_sc['emoji']} {prev_sc['title']}", prev_sc['short'], prev_sc['tag']
    involved = prev_sc['involved']

st.markdown(f"""
<div class="step-header-card">
  <div class="step-title">{h_title}</div>
  <div class="step-desc">{h_desc}</div>
  <span class="tag tag-blue">{h_tag}</span>
</div>
""", unsafe_allow_html=True)

# Buttons
c1, c2, _ = st.columns([1, 2, 4])
with c1: st.button("← Back", on_click=go_prev, disabled=(current_step == 0))
with c2: 
    if current_step < 9:
        st.button(f"Execute {SCENARIOS[current_step]['flow_label']} →", on_click=go_next, args=[selected_amount], type="primary")
    else:
        st.button("🎓 Simulation Complete", disabled=True)

