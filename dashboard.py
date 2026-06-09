"""
Revenue Intelligence — Portfolio Dashboard
Static analytics view complementing the AI chat interface.
Run: streamlit run dashboard.py
"""

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

DB_PATH = "duckdb/revenue_intel.duckdb"

COLORS = {
    "green":   "#2ecc71",
    "yellow":  "#f39c12",
    "red":     "#e74c3c",
    "blue":    "#3498db",
    "purple":  "#9b59b6",
    "slate":   "#0F172A",
    "muted":   "#64748b",
    "bg":      "#F7F8FA",
    "surface": "#FFFFFF",
    "border":  "#E2E8F0",
}

BAND_COLOR = {"green": COLORS["green"], "yellow": COLORS["yellow"], "red": COLORS["red"]}

# ── Page config ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Revenue Intelligence Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"""
<style>
    [data-testid="stAppViewContainer"] {{ background: {COLORS["bg"]}; }}
    [data-testid="stSidebar"] {{ background: {COLORS["surface"]}; border-right: 1px solid {COLORS["border"]}; }}
    .kpi-card {{
        background: {COLORS["surface"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 10px;
        padding: 1.1rem 1.4rem;
        color: {COLORS["slate"]};
    }}
    .kpi-label {{ font-size: 0.8rem; color: {COLORS["muted"]}; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }}
    .kpi-value {{ font-size: 1.8rem; font-weight: 700; color: {COLORS["slate"]}; line-height: 1.2; }}
    .kpi-sub   {{ font-size: 0.85rem; color: {COLORS["muted"]}; margin-top: 0.2rem; }}
    .band-pill {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
        color: white;
    }}
    .section-header {{
        font-size: 1.15rem;
        font-weight: 700;
        color: {COLORS["slate"]};
        margin-top: 1.8rem;
        margin-bottom: 0.3rem;
    }}
    .section-sub {{
        font-size: 0.88rem;
        color: {COLORS["muted"]};
        margin-bottom: 0.8rem;
    }}
    [data-testid="stMetricValue"] {{ font-size: 1.5rem !important; color: {COLORS["slate"]} !important; }}
    [data-testid="stMetricLabel"] {{ color: {COLORS["muted"]} !important; }}
</style>
""", unsafe_allow_html=True)

# ── Data loaders ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_health() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        select h.account_id, h.account_name, h.health_score, h.health_band,
               h.days_to_renewal, h.usage_drop_ratio, h.tickets_high, h.unpaid_invoices,
               o.current_arr_eur, o.plan, o.segment, o.owner_ae, o.renewal_date, o.subscription_status
        from fct_account_health_score h
        join dm_account_overview o using (account_id)
        order by h.health_score
    """).df()
    con.close()
    return df


@st.cache_data(ttl=60)
def load_expansion() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        select account_id, account_name, expansion_score, current_arr_eur,
               utilization, health_score, recommended_angle, supporting_signal
        from ai_fct_expansion_shortlist
        order by expansion_score desc
    """).df()
    con.close()
    return df


@st.cache_data(ttl=60)
def load_usage() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        select account_id, date_day, active_users, key_events
        from product_usage_daily
        order by account_id, date_day
    """).df()
    con.close()
    return df


# ── Sidebar ─────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💰 Revenue Intelligence")
    st.markdown("**Portfolio Dashboard**")
    st.divider()
    page = st.radio(
        "View",
        ["📊 Portfolio Overview", "🔴 Renewals at Risk", "🚀 Expansion Pipeline", "📋 Account Heatmap"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Reads from local DuckDB.\nRun `dbt seed && dbt build` to refresh.")
    st.caption("Switch to the **AI Chat** view:\n`streamlit run app.py`")


# ── Load data ───────────────────────────────────────────────────────────────────

health_df = load_health()
expansion_df = load_expansion()

total_arr = health_df["current_arr_eur"].sum()
arr_at_risk = health_df[health_df["health_band"] == "red"]["current_arr_eur"].sum()
arr_yellow = health_df[health_df["health_band"] == "yellow"]["current_arr_eur"].sum()
pct_healthy = (health_df["health_band"] == "green").mean() * 100
avg_health = health_df["health_score"].mean()
n_renewals_90d = ((health_df["days_to_renewal"] <= 90) & (health_df["days_to_renewal"] >= 0)).sum()
n_at_risk_90d = ((health_df["days_to_renewal"] <= 90) & (health_df["days_to_renewal"] >= 0) & (health_df["health_band"] == "red")).sum()


def kpi(label: str, value: str, sub: str = "") -> str:
    return f"""<div class="kpi-card">
<div class="kpi-label">{label}</div>
<div class="kpi-value">{value}</div>
{'<div class="kpi-sub">' + sub + '</div>' if sub else ''}
</div>"""


def band_pill(band: str) -> str:
    return f'<span class="band-pill" style="background:{BAND_COLOR.get(band, "#aaa")}">{band.upper()}</span>'


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1: Portfolio Overview
# ═══════════════════════════════════════════════════════════════════════════════

if page == "📊 Portfolio Overview":

    st.title("Portfolio Overview")
    st.markdown(
        "A snapshot of your entire customer base — ARR distribution by health, "
        "renewal exposure, and where the expansion opportunity sits."
    )

    # ── KPI strip ────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(kpi("Total ARR", f"€{total_arr/1_000_000:.2f}M", f"{len(health_df)} accounts"), unsafe_allow_html=True)
    c2.markdown(kpi("ARR at Risk", f"€{arr_at_risk/1_000:.0f}k",
                    f"{arr_at_risk/total_arr*100:.0f}% of portfolio (red band)"), unsafe_allow_html=True)
    c3.markdown(kpi("Healthy Accounts", f"{pct_healthy:.0f}%",
                    f"Avg health score: {avg_health:.2f}"), unsafe_allow_html=True)
    c4.markdown(kpi("Renewals in 90d", str(int(n_renewals_90d)),
                    f"{n_at_risk_90d} at-risk (red band)"), unsafe_allow_html=True)
    c5.markdown(kpi("Avg Health Score", f"{avg_health:.2f}",
                    "1.0 = perfect, 0.0 = critical"), unsafe_allow_html=True)

    st.markdown("")

    # ── ARR by health band (donut) + health score distribution ───────────────
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown('<div class="section-header">ARR by health band</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Where your revenue sits on the health spectrum. Red = churn risk. Yellow = watch closely.</div>', unsafe_allow_html=True)

        band_summary = (
            health_df.groupby("health_band")
            .agg(arr=("current_arr_eur", "sum"), n=("account_id", "count"))
            .reset_index()
        )
        band_summary["pct"] = band_summary["arr"] / band_summary["arr"].sum() * 100

        fig_donut = go.Figure(go.Pie(
            labels=band_summary["health_band"].str.capitalize(),
            values=band_summary["arr"],
            hole=0.58,
            marker_colors=[BAND_COLOR.get(b, "#aaa") for b in band_summary["health_band"]],
            textinfo="label+percent",
            textfont_size=13,
            hovertemplate="<b>%{label}</b><br>ARR: €%{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        fig_donut.update_layout(
            height=300, margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False, paper_bgcolor="white",
            annotations=[dict(text=f"€{total_arr/1_000_000:.1f}M", x=0.5, y=0.5,
                              font_size=18, font_color=COLORS["slate"], showarrow=False)],
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        # Band summary table
        c_slate = COLORS["slate"]
        c_muted = COLORS["muted"]
        for _, r in band_summary.sort_values("arr", ascending=False).iterrows():
            pill = band_pill(r["health_band"])
            arr_str = f"{r['arr']/1_000:.0f}k"
            n_str = f"{int(r['n'])} accounts ({r['pct']:.0f}%)"
            st.markdown(
                f"{pill} &nbsp; "
                f"<span style='color:{c_slate};font-weight:600'>€{arr_str}</span> "
                f"<span style='color:{c_muted};font-size:0.85rem'>across {n_str}</span>",
                unsafe_allow_html=True,
            )

    with col_right:
        st.markdown('<div class="section-header">Health score distribution</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Each bar is one account. Scores below 0.5 are red — those need action now.</div>', unsafe_allow_html=True)

        fig_hist = go.Figure()
        for band, color in BAND_COLOR.items():
            subset = health_df[health_df["health_band"] == band]
            fig_hist.add_trace(go.Bar(
                x=subset["account_name"],
                y=subset["health_score"],
                name=band.capitalize(),
                marker_color=color,
                hovertemplate="<b>%{x}</b><br>Health: %{y:.2f}<extra></extra>",
            ))
        fig_hist.add_hline(y=0.75, line_dash="dot", line_color=COLORS["green"],
                           annotation_text="Green threshold", annotation_position="right")
        fig_hist.add_hline(y=0.5, line_dash="dot", line_color=COLORS["red"],
                           annotation_text="Red threshold", annotation_position="right")
        fig_hist.update_layout(
            height=300, barmode="stack",
            margin=dict(t=10, b=80, l=40, r=80),
            yaxis=dict(title="Health score", range=[0, 1.05], showgrid=True, gridcolor="#eee"),
            xaxis=dict(showticklabels=True, tickangle=-35, tickfont=dict(size=10)),
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", y=-0.45),
            showlegend=True,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # ── Risk driver breakdown ─────────────────────────────────────────────────
    st.markdown('<div class="section-header">Primary risk drivers across portfolio</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">What is driving health score down? Each column is an independent risk signal.</div>', unsafe_allow_html=True)

    risk_cols = st.columns(4)
    drivers = {
        "Usage declining": (health_df["usage_drop_ratio"] >= 0.15).sum(),
        "Unpaid invoices": (health_df["unpaid_invoices"] > 0).sum(),
        "High-sev tickets": (health_df["tickets_high"] >= 1).sum(),
        "Renewal in 90d": ((health_df["days_to_renewal"] >= 0) & (health_df["days_to_renewal"] <= 90)).sum(),
    }
    icons = ["📉", "💳", "🎫", "📅"]
    for col, (label, count), icon in zip(risk_cols, drivers.items(), icons):
        pct = count / len(health_df) * 100
        col.markdown(
            kpi(f"{icon} {label}", str(int(count)), f"{pct:.0f}% of accounts affected"),
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2: Renewals at Risk
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "🔴 Renewals at Risk":

    st.title("Renewals at Risk")
    st.markdown(
        "Accounts renewing in the next 90 days, sorted by urgency. "
        "The sooner the renewal and the lower the health score, the higher the risk."
    )

    with st.expander("ℹ️  How to use this view"):
        st.markdown("""
- **Days to renewal** — negative means the renewal date has already passed. Follow up immediately.
- **Health score** — below 0.5 (red) means multiple risk signals are active. Do not wait for the QBR.
- **Primary risk driver** — the single biggest factor pulling the health score down. Start the conversation there.
- **Action**: CS should open an account deep-dive in the AI Chat view (`streamlit run app.py`) to get a talk track and suggested next steps.
        """)

    # Filters
    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        horizon = st.selectbox("Renewal horizon", [30, 60, 90, 180], index=2, format_func=lambda x: f"Next {x} days")
    with f2:
        health_thresh = st.slider("Max health score", 0.0, 1.0, 0.75, 0.05)

    at_risk = health_df[
        (health_df["days_to_renewal"] <= horizon) &
        (health_df["health_score"] < health_thresh)
    ].copy().sort_values(["health_score", "days_to_renewal"])

    arr_window = at_risk["current_arr_eur"].sum()
    r1, r2, r3 = st.columns(3)
    r1.metric("Accounts at risk", len(at_risk), help="Renewal in window + below health threshold")
    r2.metric("ARR at risk", f"€{arr_window/1_000:.0f}k", help="Total ARR of at-risk accounts")
    r3.metric("Avg health score", f"{at_risk['health_score'].mean():.2f}" if len(at_risk) else "—")

    # Gantt-style renewal timeline
    st.markdown('<div class="section-header">Renewal timeline</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Each bar = one account. Position = days to renewal. Color = health band. Length = ARR (scaled).</div>', unsafe_allow_html=True)

    if len(at_risk) > 0:
        fig_gantt = go.Figure()
        for _, row in at_risk.iterrows():
            color = BAND_COLOR.get(row["health_band"], "#aaa")
            fig_gantt.add_trace(go.Bar(
                x=[max(row["days_to_renewal"], 1)],
                y=[row["account_name"]],
                orientation="h",
                marker_color=color,
                text=f"€{row['current_arr_eur']/1_000:.0f}k · {row['days_to_renewal']}d",
                textposition="inside",
                textfont=dict(color="white", size=11),
                hovertemplate=(
                    f"<b>{row['account_name']}</b><br>"
                    f"Health: {row['health_score']:.2f} ({row['health_band']})<br>"
                    f"Days to renewal: {row['days_to_renewal']}<br>"
                    f"ARR: €{row['current_arr_eur']:,.0f}<extra></extra>"
                ),
                showlegend=False,
            ))
        fig_gantt.add_vline(x=30, line_dash="dot", line_color=COLORS["red"],
                            annotation_text="30d", annotation_position="top")
        fig_gantt.add_vline(x=60, line_dash="dot", line_color=COLORS["yellow"],
                            annotation_text="60d", annotation_position="top")
        fig_gantt.update_layout(
            height=max(250, len(at_risk) * 40),
            margin=dict(t=30, b=40, l=160, r=40),
            xaxis=dict(title="Days to renewal", showgrid=True, gridcolor="#eee"),
            yaxis=dict(showgrid=False, autorange="reversed"),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

    # Detail table
    st.markdown('<div class="section-header">Account detail</div>', unsafe_allow_html=True)
    if len(at_risk) > 0:
        display = at_risk[[
            "account_name", "health_band", "health_score", "days_to_renewal",
            "current_arr_eur", "usage_drop_ratio", "tickets_high", "unpaid_invoices", "owner_ae"
        ]].copy()
        display.columns = ["Account", "Band", "Health", "Days to Renewal",
                           "ARR (€)", "Usage Drop", "High Tickets", "Unpaid Invoices", "AE Owner"]
        display["Health"] = display["Health"].round(2)
        display["Usage Drop"] = (display["Usage Drop"] * 100).round(1).astype(str) + "%"
        display["ARR (€)"] = display["ARR (€)"].map(lambda x: f"€{x:,.0f}")
        st.dataframe(display.set_index("Account"), use_container_width=True)
        st.caption(f"Showing {len(at_risk)} accounts renewing in {horizon} days with health < {health_thresh}. "
                   "Open the AI Chat view for a talk track and next best action per account.")
    else:
        st.success(f"No accounts renewing in the next {horizon} days with health score below {health_thresh:.2f}.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3: Expansion Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "🚀 Expansion Pipeline":

    st.title("Expansion Pipeline")
    st.markdown(
        "Accounts ranked by their likelihood to expand — based on health score, seat utilization, "
        "and usage signals. Green + high utilization = strongest upsell case."
    )

    with st.expander("ℹ️  How expansion score is calculated"):
        st.markdown("""
**Expansion score** = 0.5 × health score + 0.5 × seat utilization ratio

- **Health score** — a sick account won't expand. Health must be strong before upsell conversations start.
- **Seat utilization** — if 90%+ of purchased seats are active, the customer has outgrown their plan. That's a natural opening for a seat expansion conversation.
- **Recommended angle** — determined by the combination of health + utilization:
  - *Add seats* — utilization ≥ 85%, already at capacity
  - *Upgrade plan / add module* — health ≥ 70%, growth trajectory
  - *Adoption + expansion later* — usage still low, build engagement first
  - *Review opportunity* — health or usage signals need investigation before pursuing
        """)

    e1, e2, e3, e4 = st.columns(4)
    top_candidates = expansion_df[expansion_df["expansion_score"] >= 0.7]
    e1.metric("Strong candidates", len(top_candidates), help="Expansion score ≥ 0.7")
    e2.metric("Avg expansion score", f"{expansion_df['expansion_score'].mean():.2f}")
    e3.metric("ARR in strong pipeline", f"€{top_candidates['current_arr_eur'].sum()/1_000:.0f}k")
    e4.metric("Avg seat utilization", f"{expansion_df['utilization'].mean()*100:.0f}%")

    col_l, col_r = st.columns([1.2, 1])

    with col_l:
        st.markdown('<div class="section-header">Expansion score by account</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Sorted by score. Color = recommended angle.</div>', unsafe_allow_html=True)

        angle_colors = {
            "Add seats": COLORS["green"],
            "Upgrade plan / add module": COLORS["blue"],
            "Adoption + expansion later": COLORS["yellow"],
            "Review opportunity": COLORS["red"],
        }

        fig_exp = go.Figure()
        for angle, color in angle_colors.items():
            subset = expansion_df[expansion_df["recommended_angle"] == angle]
            if len(subset):
                fig_exp.add_trace(go.Bar(
                    x=subset["expansion_score"],
                    y=subset["account_name"],
                    orientation="h",
                    name=angle,
                    marker_color=color,
                    text=subset["expansion_score"].round(2),
                    textposition="inside",
                    textfont=dict(color="white", size=11),
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Expansion score: %{x:.2f}<br>"
                        f"Angle: {angle}<extra></extra>"
                    ),
                ))
        fig_exp.add_vline(x=0.7, line_dash="dot", line_color=COLORS["green"],
                          annotation_text="Strong (0.7)", annotation_position="top")
        fig_exp.update_layout(
            height=max(300, len(expansion_df) * 36),
            barmode="stack",
            margin=dict(t=30, b=40, l=170, r=40),
            xaxis=dict(title="Expansion score", range=[0, 1.05], showgrid=True, gridcolor="#eee"),
            yaxis=dict(showgrid=False, autorange="reversed", categoryorder="total ascending"),
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", y=-0.15, font_size=11),
        )
        st.plotly_chart(fig_exp, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Health vs utilization</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Top-right quadrant = ship the upsell now.</div>', unsafe_allow_html=True)

        fig_scatter = go.Figure()
        for angle, color in angle_colors.items():
            subset = expansion_df[expansion_df["recommended_angle"] == angle]
            if len(subset):
                fig_scatter.add_trace(go.Scatter(
                    x=subset["health_score"],
                    y=subset["utilization"],
                    mode="markers+text",
                    name=angle,
                    marker=dict(color=color, size=subset["current_arr_eur"].clip(5000, 300000) / 8000 + 8,
                                line=dict(color="white", width=1.5)),
                    text=subset["account_name"].str.split().str[0],
                    textposition="top center",
                    textfont=dict(size=9, color=COLORS["slate"]),
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "Health: %{x:.2f}<br>Utilization: %{y:.0%}<extra></extra>"
                    ),
                    showlegend=False,
                ))

        fig_scatter.add_vline(x=0.75, line_dash="dot", line_color="#ccc")
        fig_scatter.add_hline(y=0.75, line_dash="dot", line_color="#ccc")
        fig_scatter.add_annotation(x=0.9, y=0.95, text="🚀 Ship it", showarrow=False,
                                   font=dict(color=COLORS["green"], size=11))
        fig_scatter.add_annotation(x=0.2, y=0.95, text="⚠️ Usage ok,\nhealth risk", showarrow=False,
                                   font=dict(color=COLORS["yellow"], size=10))
        fig_scatter.update_layout(
            height=420,
            margin=dict(t=20, b=50, l=60, r=20),
            xaxis=dict(title="Health score", range=[0, 1.05], showgrid=True, gridcolor="#eee"),
            yaxis=dict(title="Seat utilization", tickformat=".0%", range=[0, 1.1],
                       showgrid=True, gridcolor="#eee"),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Top 10 table
    st.markdown('<div class="section-header">Top expansion candidates</div>', unsafe_allow_html=True)
    top10 = expansion_df.head(10).copy()
    top10["expansion_score"] = top10["expansion_score"].round(2)
    top10["health_score"] = top10["health_score"].round(2)
    top10["utilization"] = (top10["utilization"] * 100).round(1).astype(str) + "%"
    top10["current_arr_eur"] = top10["current_arr_eur"].map(lambda x: f"€{x:,.0f}")
    top10 = top10.rename(columns={
        "account_name": "Account", "expansion_score": "Score",
        "health_score": "Health", "utilization": "Seat utilization",
        "current_arr_eur": "ARR", "recommended_angle": "Recommended angle",
    })
    st.dataframe(top10[["Account", "Score", "Health", "Seat utilization", "ARR", "Recommended angle"]]
                 .set_index("Account"), use_container_width=True)
    st.caption("Bubble size in scatter = ARR. Open the AI Chat view for deal-specific talk tracks.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4: Account Heatmap
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📋 Account Heatmap":

    st.title("Account Heatmap")
    st.markdown(
        "All accounts ranked by health score. Each row is one account. "
        "Each column is a risk signal. Red = active risk. Scan for patterns across your book of business."
    )

    # Filters
    f1, f2 = st.columns([1, 1])
    with f1:
        band_filter = st.multiselect(
            "Health band", ["green", "yellow", "red"],
            default=["green", "yellow", "red"],
        )
    with f2:
        seg_filter = st.multiselect(
            "Segment", sorted(health_df["segment"].unique()),
            default=sorted(health_df["segment"].unique()),
        )

    filtered = health_df[
        health_df["health_band"].isin(band_filter) &
        health_df["segment"].isin(seg_filter)
    ].copy()

    # Build heatmap data
    hm_data = filtered[[
        "account_name", "health_score", "usage_drop_ratio", "tickets_high",
        "unpaid_invoices", "days_to_renewal", "current_arr_eur", "health_band",
        "segment", "plan", "owner_ae"
    ]].copy()

    hm_data["usage_risk"] = (hm_data["usage_drop_ratio"] >= 0.15).astype(int)
    hm_data["ticket_risk"] = (hm_data["tickets_high"] >= 1).astype(int)
    hm_data["payment_risk"] = (hm_data["unpaid_invoices"] > 0).astype(int)
    hm_data["renewal_risk"] = ((hm_data["days_to_renewal"] >= 0) & (hm_data["days_to_renewal"] <= 90)).astype(int)

    risk_signals = ["usage_risk", "ticket_risk", "payment_risk", "renewal_risk"]
    z = hm_data[risk_signals].values.T.tolist()
    x = hm_data["account_name"].tolist()
    y = ["Usage\ndecline", "High-sev\nticket", "Unpaid\ninvoice", "Renewal\n<90d"]

    fig_hm = go.Figure(go.Heatmap(
        z=z, x=x, y=y,
        colorscale=[[0, "#eafaf1"], [1, "#e74c3c"]],
        showscale=False,
        xgap=2, ygap=2,
        hovertemplate="<b>%{x}</b><br>%{y}: %{z}<extra></extra>",
        text=[["Active" if v else "—" for v in row] for row in z],
        texttemplate="%{text}",
        textfont=dict(size=11),
    ))
    fig_hm.update_layout(
        height=250,
        margin=dict(t=20, b=80, l=100, r=20),
        xaxis=dict(showgrid=False, tickangle=-40, tickfont=dict(size=10)),
        yaxis=dict(showgrid=False, tickfont=dict(size=11)),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    st.plotly_chart(fig_hm, use_container_width=True)

    # Sortable full table
    st.markdown('<div class="section-header">Full account table</div>', unsafe_allow_html=True)

    table = filtered[[
        "account_name", "health_band", "health_score", "current_arr_eur",
        "days_to_renewal", "usage_drop_ratio", "tickets_high", "unpaid_invoices",
        "plan", "segment", "owner_ae"
    ]].copy()
    table["health_score"] = table["health_score"].round(2)
    table["usage_drop_ratio"] = (table["usage_drop_ratio"] * 100).round(1).astype(str) + "%"
    table["current_arr_eur"] = table["current_arr_eur"].map(lambda x: f"€{x:,.0f}")
    table.columns = [
        "Account", "Band", "Health", "ARR",
        "Days to Renewal", "Usage Drop", "High Tickets", "Unpaid Invoices",
        "Plan", "Segment", "AE"
    ]
    st.dataframe(
        table.set_index("Account").sort_values("Health"),
        use_container_width=True,
        height=400,
    )
    st.caption(
        f"Showing {len(filtered)} accounts. "
        "Click column headers to sort. Open the AI Chat view for account-level talk tracks."
    )
