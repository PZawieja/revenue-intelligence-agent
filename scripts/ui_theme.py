import streamlit as st

# Sanity checklist:
# - If a component background is dark, use text_on_dark.
# - If a component background is primary, use text_on_primary.
# - Default surfaces use text.

CONTRAST_AUDIT = False

THEME = {
    "bg": "#F7F8FA",
    "surface": "#FFFFFF",
    "surface_2": "#F2F4F7",
    "border": "#E5E7EB",
    "text": "#0B1220",
    "text_muted": "#5B667A",
    "text_on_dark": "#FFFFFF",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "text_on_primary": "#FFFFFF",
}

def inject_css():
    audit_outline = "2px dashed #F59E0B" if CONTRAST_AUDIT else "none"
    st.markdown(
        f"""
<style>
:root {{
  --ri-bg: {THEME["bg"]};
  --ri-surface: {THEME["surface"]};
  --ri-surface-2: {THEME["surface_2"]};
  --ri-border: {THEME["border"]};
  --ri-text: {THEME["text"]};
  --ri-text-muted: {THEME["text_muted"]};
  --ri-text-on-dark: {THEME["text_on_dark"]};
  --ri-primary: {THEME["primary"]};
  --ri-primary-hover: {THEME["primary_hover"]};
  --ri-text-on-primary: {THEME["text_on_primary"]};
  color-scheme: light !important;
}}

html, body, [data-testid="stAppViewContainer"] {{
  background: var(--ri-bg);
  color: var(--ri-text);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
  color-scheme: light;
}}
html, body {{
  background: var(--ri-bg) !important;
}}
[data-testid="stApp"] {{
  background: var(--ri-bg);
}}
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stSidebar"],
section.main,
.stApp {{
  background: var(--ri-bg) !important;
  color: var(--ri-text) !important;
}}
[data-testid="stToolbar"],
[data-testid="stDecoration"],
footer {{
  background: var(--ri-bg) !important;
  color: var(--ri-text) !important;
}}

/* prevent any dark panels/popovers/expanders */
div[role="dialog"],
div[role="menu"],
div[role="listbox"],
[data-baseweb="popover"],
[data-baseweb="menu"],
[data-baseweb="select"],
[data-baseweb="tooltip"],
[data-testid="stPopover"],
[data-testid="stExpander"],
[data-testid="stExpanderDetails"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stContainer"] {{
  background: var(--ri-surface) !important;
  color: var(--ri-text) !important;
  border-color: var(--ri-border) !important;
}}

div[role="dialog"],
[data-baseweb="popover"],
[data-testid="stPopover"] {{
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 16px !important;
}}

[data-testid="stHeader"] {{
  background: transparent;
}}

.app-container {{
  max-width: 980px;
  margin: 0 auto;
}}

/* Chat feed container */
[data-testid="stChatMessage"] {{
  max-width: 900px;
  margin-left: auto;
  margin-right: auto;
  padding-bottom: 8px;
}}
.message-row {{
  max-width: 720px;
}}

.workspace-card {{
  background: var(--ri-surface);
  border: 1px solid var(--ri-border);
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}}

h1, h2, h3, h4, h5 {{
  color: var(--ri-text);
  font-weight: 700;
}}

.ri-subtitle {{
  color: var(--ri-text-muted);
  font-size: 0.95rem;
  margin-top: 0;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
  background: var(--ri-surface-2);
  border-right: 1px solid var(--ri-border);
}}
[data-testid="stSidebar"] * {{
  color: var(--ri-text) !important;
}}

/* Sidebar collapse/expand control */
[data-testid="stSidebarCollapsedControl"],
button[aria-label*="sidebar"],
button[title*="sidebar"] {{
  background: var(--ri-surface) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 10px !important;
  opacity: 1 !important;
  color: var(--ri-text) !important;
}}
 [data-testid="stSidebarCollapsedControl"] *,
button[aria-label*="sidebar"] *,
button[title*="sidebar"] * {{
  color: var(--ri-text) !important;
}}
[data-testid="stSidebarCollapsedControl"] svg,
button[aria-label*="sidebar"] svg,
button[title*="sidebar"] svg {{
  fill: var(--ri-text) !important;
  color: var(--ri-text) !important;
  opacity: 1 !important;
}}
button[aria-label="Expand sidebar"],
button[aria-label="Collapse sidebar"] {{
  background: var(--ri-surface) !important;
  border: 1px solid var(--ri-border) !important;
  color: var(--ri-text) !important;
}}
button[aria-label="Expand sidebar"] svg,
button[aria-label="Collapse sidebar"] svg {{
  fill: var(--ri-text) !important;
  color: var(--ri-text) !important;
}}

/* Labels, inputs */
label {{
  color: var(--ri-text) !important;
  font-weight: 600;
}}
input, textarea, select {{
  color: var(--ri-text) !important;
  background: var(--ri-surface) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 12px !important;
}}
input::placeholder, textarea::placeholder {{
  color: var(--ri-text-muted) !important;
}}

div[data-baseweb="select"] > div {{
  background: var(--ri-surface) !important;
  border-radius: 12px !important;
  border: 1px solid var(--ri-border) !important;
  color: var(--ri-text) !important;
}}
div[data-baseweb="select"] span {{
  color: var(--ri-text) !important;
}}

/* Buttons */
button[kind="primary"] {{
  background: var(--ri-primary) !important;
  color: var(--ri-text-on-primary) !important;
  border: none !important;
  border-radius: 12px !important;
  padding: 0.5rem 0.9rem !important;
  font-weight: 600 !important;
}}
button[kind="primary"]:hover {{
  background: var(--ri-primary-hover) !important;
}}
.stButton > button[kind="secondary"],
button[kind="secondary"] {{
  background: transparent !important;
  color: var(--ri-text-muted) !important;
  border: none !important;
  padding: 0.15rem 0.3rem !important;
  font-weight: 600 !important;
  font-size: 0.8rem !important;
}}
.stButton > button[kind="secondary"]:hover,
button[kind="secondary"]:hover {{
  background: var(--ri-surface-2) !important;
  color: var(--ri-text) !important;
}}

/* Global button overrides */
.stButton > button:not([kind="primary"]),
button[data-baseweb="button"]:not([kind="primary"]),
[role="button"]:not([kind="primary"]) {{
  background: var(--ri-surface) !important;
  color: var(--ri-text) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  outline: none !important;
}}
.stButton > button:not([kind="primary"]):hover,
button[data-baseweb="button"]:not([kind="primary"]):hover,
[role="button"]:not([kind="primary"]):hover {{
  background: var(--ri-surface-2) !important;
  color: var(--ri-text) !important;
  border-color: var(--ri-border) !important;
}}
.stButton > button:not([kind="primary"]):active,
button[data-baseweb="button"]:not([kind="primary"]):active,
[role="button"]:not([kind="primary"]):active {{
  background: var(--ri-surface-2) !important;
  color: var(--ri-text) !important;
}}
.stButton > button:not([kind="primary"]):focus,
.stButton > button:not([kind="primary"]):focus-visible,
button[data-baseweb="button"]:not([kind="primary"]):focus,
button[data-baseweb="button"]:not([kind="primary"]):focus-visible,
[role="button"]:not([kind="primary"]):focus,
[role="button"]:not([kind="primary"]):focus-visible {{
  outline: 2px solid var(--ri-primary) !important;
  outline-offset: 2px !important;
}}
.stButton > button:not([kind="primary"]):disabled,
button[data-baseweb="button"]:not([kind="primary"]):disabled,
[role="button"]:not([kind="primary"]):disabled {{
  background: var(--ri-surface) !important;
  color: var(--ri-text-muted) !important;
  border-color: var(--ri-border) !important;
}}

/* Tiles */
.tile-grid .stButton > button {{
  background: var(--ri-surface) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 12px !important;
  padding: 12px 14px !important;
  font-weight: 600 !important;
  color: var(--ri-text) !important;
}}
.tile-grid .stButton > button:hover {{
  background: var(--ri-surface-2) !important;
  border-color: var(--ri-border) !important;
  color: var(--ri-text) !important;
}}
.tile-grid .stButton > button:active {{
  background: var(--ri-surface-2) !important;
}}
.tile-grid .stButton > button:focus,
.tile-grid .stButton > button:focus-visible {{
  outline: 2px solid var(--ri-primary) !important;
  outline-offset: 2px !important;
}}

/* Pills */
.pill .stButton > button {{
  background: var(--ri-surface) !important;
  border: 1px solid var(--ri-border) !important;
  color: var(--ri-text) !important;
  border-radius: 999px !important;
  padding: 0.3rem 0.65rem !important;
  font-weight: 600 !important;
  font-size: 0.82rem !important;
}}
.pill .stButton > button:hover {{
  background: var(--ri-surface-2) !important;
}}
.pill {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}}

.suggestion-label {{
  font-size: 12px;
  color: var(--ri-text-muted);
  margin-top: 10px;
}}
.suggestion-row {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}}
.suggestion-row .stButton > button {{
  background: var(--ri-surface) !important;
  border: 1px solid var(--ri-border) !important;
  color: var(--ri-text) !important;
  border-radius: 999px !important;
  padding: 6px 10px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}}
.suggestion-row .stButton > button:hover {{
  background: var(--ri-surface-2) !important;
  color: var(--ri-text) !important;
}}
.suggestion-row .stButton > button:active {{
  background: var(--ri-surface-2) !important;
  color: var(--ri-text) !important;
}}
.suggestion-row .stButton > button:focus,
.suggestion-row .stButton > button:focus-visible {{
  outline: 2px solid var(--ri-border) !important;
  outline-offset: 2px !important;
  color: var(--ri-text) !important;
}}
.suggestion-row .stButton > button:disabled {{
  background: var(--ri-surface) !important;
  color: var(--ri-text-muted) !important;
  border-color: var(--ri-border) !important;
}}
.suggestion-row .stButton > button:active,
.suggestion-row .stButton > button:focus,
.suggestion-row .stButton > button:focus-visible {{
  outline: 2px solid var(--ri-border) !important;
  outline-offset: 2px !important;
}}

.quick-link .stButton > button {{
  background: transparent !important;
  color: var(--ri-text-muted) !important;
  border: none !important;
  padding: 0 !important;
  font-size: 12.5px !important;
  font-weight: 600 !important;
}}
.quick-link .stButton > button:hover {{
  color: var(--ri-text) !important;
}}
.quick-link .stButton > button:active,
.quick-link .stButton > button:focus,
.quick-link .stButton > button:focus-visible {{
  color: var(--ri-text) !important;
  outline: none !important;
}}
.quick-link .stButton > button:disabled {{
  color: var(--ri-text-muted) !important;
}}

.quick-mini {{
  margin-top: 6px;
}}

/* Quick questions popover */
.quickq-popover {{
  background: var(--ri-surface) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 16px !important;
  padding: 12px !important;
  max-width: 600px !important;
  max-height: 220px !important;
  overflow-y: auto !important;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12) !important;
}}
.quickq-row {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}}
.quickq-popover .stButton > button {{
  background: var(--ri-surface) !important;
  color: var(--ri-text) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 999px !important;
  padding: 6px 10px !important;
  font-size: 13px !important;
  line-height: 1.1 !important;
  box-shadow: none !important;
  max-width: 260px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}}
.quickq-popover .stButton > button:hover {{
  background: var(--ri-surface-2) !important;
}}
.quickq-popover .stButton > button:active,
.quickq-popover .stButton > button:focus {{
  outline: none !important;
  box-shadow: 0 0 0 3px rgba(47, 107, 255, 0.15) !important;
}}

/* Chips */
.chip-row {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 8px 0 12px 0;
}}
.chip {{
  background: var(--ri-surface-2);
  color: var(--ri-text);
  border: 1px solid var(--ri-border);
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 0.78rem;
  font-weight: 600;
}}

/* Answer card */
.answer-card {{
  background: var(--ri-surface);
  border: 1px solid var(--ri-border);
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
  max-width: 720px;
  margin-bottom: 8px;
}}
.answer-title {{
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--ri-text);
}}
.badge-governed {{
  background: var(--ri-surface-2);
  border: 1px solid var(--ri-border);
  color: var(--ri-text-muted);
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 600;
  margin-left: 6px;
  display: inline-block;
}}
.answer-muted {{
  color: var(--ri-text-muted);
}}
.so-what {{
  color: var(--ri-text-muted);
  font-size: 13px;
  margin-top: 8px;
}}
.answer-summary {{
  color: var(--ri-text);
  font-size: 0.95rem;
  margin: 6px 0 8px 0;
  line-height: 1.4;
}}
.next-best-action {{
  color: var(--ri-text);
  font-size: 13px;
  margin-top: 10px;
  padding: 8px 0;
}}
.next-best-action strong {{
  color: var(--ri-text);
}}
.talk-track {{
  color: var(--ri-text-muted);
  font-size: 12.5px;
  font-style: italic;
  margin-top: 6px;
  padding: 6px 0;
}}
.guardrail-meta {{
  color: var(--ri-text-muted);
  font-size: 13px;
  margin-top: 6px;
}}
.answer-list {{
  margin: 8px 0 6px 18px;
}}
.details-section {{
  border-top: 1px solid var(--ri-border);
  margin-top: 12px;
  padding-top: 10px;
}}

.kpi-row {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 8px 0 10px 0;
}}
.kpi-chip {{
  font-size: 12.5px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--ri-border);
  background: var(--ri-surface-2);
  color: var(--ri-text);
  font-weight: 600;
}}
.kpi-good {{
  background: #EAF7EF;
  border-color: #DCEFE4;
  color: #167A3E;
}}
.kpi-warn {{
  background: #FFF6E6;
  border-color: #FCE8C7;
  color: #8A5A14;
}}
.kpi-bad {{
  background: #FCEEEE;
  border-color: #F7D9D9;
  color: #9A2A2A;
}}

.kv-card {{
  background: var(--ri-surface);
  border: 1px solid var(--ri-border);
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 8px;
}}
.kv-key {{
  font-size: 0.75rem;
  color: var(--ri-text-muted);
  margin-bottom: 4px;
}}
.kv-value {{
  font-size: 0.95rem;
  color: var(--ri-text);
  font-weight: 600;
}}

.chip-green {{
  background: #EAF7EF;
  border-color: #DCEFE4;
  color: #167A3E;
}}
.chip-yellow {{
  background: #FFF6E6;
  border-color: #FCE8C7;
  color: #8A5A14;
}}
.chip-red {{
  background: #FCEEEE;
  border-color: #F7D9D9;
  color: #9A2A2A;
}}
.chip-high {{
  background: #EAF7EF;
  border-color: #DCEFE4;
  color: #167A3E;
}}
.chip-medium {{
  background: #FFF6E6;
  border-color: #FCE8C7;
  color: #8A5A14;
}}
.chip-low {{
  background: #FCEEEE;
  border-color: #F7D9D9;
  color: #9A2A2A;
}}

/* Avatar badges */
.badge {{
  width: 26px;
  height: 26px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
}}
.badge-bot {{
  background: var(--ri-primary);
  color: var(--ri-text-on-primary);
}}
.badge-human {{
  background: var(--ri-surface-2);
  color: var(--ri-text);
}}

/* Tabs */
div[data-baseweb="tab-list"] button {{
  font-weight: 600 !important;
  color: var(--ri-text) !important;
  border-radius: 999px !important;
  padding: 0.35rem 0.75rem !important;
}}

/* Details segmented control (radio) */
[data-testid="stRadio"] {{
  background: transparent !important;
}}
[data-testid="stRadio"] * {{
  color: var(--ri-text) !important;
}}
[data-testid="stRadio"] div[role="radiogroup"] {{
  background: var(--ri-surface-2) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 999px !important;
  padding: 4px !important;
  gap: 4px !important;
}}
[data-testid="stRadio"] label {{
  margin: 0 !important;
}}
[data-testid="stRadio"] div[role="radio"] {{
  background: var(--ri-surface) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 999px !important;
  padding: 4px 10px !important;
}}
[data-testid="stRadio"] input:checked + div {{
  background: var(--ri-surface) !important;
  border-color: var(--ri-text) !important;
}}
[data-testid="stRadio"] input:checked + div span,
[data-testid="stRadio"] div[role="radio"] span {{
  color: var(--ri-text) !important;
}}
[data-testid="stRadio"] div[role="radio"] {{
  box-shadow: none !important;
}}

/* Expanders and debug labels */
div[data-testid="stExpander"] summary {{
  color: var(--ri-text) !important;
  background: var(--ri-surface) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 12px !important;
  padding: 8px 10px !important;
}}
div[data-testid="stExpander"] {{
  background: transparent !important;
}}
div[data-testid="stExpander"] > details {{
  background: transparent !important;
  border: none !important;
}}

/* Code blocks */
code, pre, .stCodeBlock, [data-testid="stCodeBlock"] {{
  color: var(--ri-text) !important;
  background: var(--ri-surface) !important;
  border-radius: 10px !important;
  border: 1px solid var(--ri-border) !important;
  font-size: 0.85rem !important;
}}


/* Chat bubbles + badges */
.chat-bubble {{
  background: var(--ri-surface-2);
  border: 1px solid var(--ri-border);
  border-radius: 12px;
  padding: 10px 12px;
  max-width: 720px;
}}
.chat-bubble-user {{
  background: var(--ri-surface-2);
  border-radius: 14px;
}}

.executed-sql {{
  color: var(--ri-text-muted);
  font-size: 0.8rem;
  margin-top: 6px;
}}
.badge {{
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
}}
.badge-bot {{
  background: var(--ri-primary);
  color: var(--ri-text-on-primary);
}}
.badge-human {{
  background: var(--ri-surface-2);
  color: var(--ri-text);
}}

/* Chat input */
[data-testid="stChatInput"] {{
  background: var(--ri-bg) !important;
  border-top: none !important;
}}
[data-testid="stChatInput"] * {{
  background: var(--ri-bg) !important;
}}
[data-testid="stChatInput"] textarea:focus {{
  box-shadow: none !important;
}}

/* Bottom container strip */
[data-testid="stBottom"] {{
  background: var(--ri-bg) !important;
  border-top: none !important;
}}
[data-testid="stBottomBlockContainer"] {{
  background: var(--ri-bg) !important;
}}
[data-testid="stBottomBlockContainer"] * {{
  background: var(--ri-bg) !important;
}}
[data-testid="stChatInput"] textarea {{
  background: var(--ri-surface) !important;
  color: var(--ri-text) !important;
  border: 1px solid var(--ri-border) !important;
  border-radius: 12px !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{
  color: var(--ri-text-muted) !important;
}}

.stMarkdown, .stText, .stCaption {{
  color: var(--ri-text) !important;
}}

/* Contrast audit outlines */
div[data-testid="stButton"] > button,
button[data-baseweb="button"],
[role="button"],
input, textarea, select,
div[data-testid="stExpander"] summary {{
  outline: {audit_outline};
  outline-offset: 1px;
}}
</style>
        """,
        unsafe_allow_html=True,
    )
