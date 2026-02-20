import streamlit as st

# Sanity checklist:
# - If a component background is dark, use text_on_dark.
# - If a component background is primary, use text_on_primary.
# - Default surfaces use text.

CONTRAST_AUDIT = True

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
}}

html, body, [data-testid="stAppViewContainer"] {{
  background: var(--ri-bg);
  color: var(--ri-text);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
  color-scheme: light;
}}

[data-testid="stHeader"] {{
  background: transparent;
}}

.app-container {{
  max-width: 1100px;
  margin: 0 auto;
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
  padding: 0.35rem 0.7rem !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
}}

/* Answer card */
.answer-card {{
  background: var(--ri-surface);
  border: 1px solid var(--ri-border);
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
}}
.answer-label {{
  font-size: 0.75rem;
  color: var(--ri-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}}
.answer-title {{
  font-size: 1.05rem;
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--ri-text);
}}
.answer-muted {{
  color: var(--ri-text-muted);
}}

/* Tabs */
div[data-baseweb="tab-list"] button {{
  font-weight: 600 !important;
  color: var(--ri-text) !important;
  border-radius: 999px !important;
  padding: 0.35rem 0.75rem !important;
}}

/* Expanders and debug labels */
div[data-testid="stExpander"] summary {{
  color: var(--ri-text) !important;
}}

/* Code blocks */
code, pre {{
  color: var(--ri-text) !important;
  background: var(--ri-surface) !important;
  border-radius: 10px !important;
  border: 1px solid var(--ri-border) !important;
  font-size: 0.85rem !important;
}}

/* Chat input */
[data-testid="stChatInput"] {{
  background: var(--ri-bg) !important;
  border-top: 1px solid var(--ri-border) !important;
}}
[data-testid="stChatInput"] textarea {{
  background: var(--ri-surface) !important;
  color: var(--ri-text) !important;
  border: 1px solid var(--ri-border) !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{
  color: var(--ri-text-muted) !important;
}}

/* Chat bubbles */
.chat-bubble {{
  background: var(--ri-surface);
  border: 1px solid var(--ri-border);
  border-radius: 14px;
  padding: 12px 14px;
}}
.chat-title {{
  font-weight: 700;
  margin-bottom: 4px;
  color: var(--ri-text);
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
