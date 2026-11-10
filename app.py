import streamlit as st
import plotly.graph_objects as go

from data import get_chain, make_sample_chain
from gex import add_gex, find_gamma_flip, find_walls
from gex import gex_by_strike, gex_by_expiry


TEXT = "#8b91a3"
STRONG = "#f2f3f5"
FAINT = "#4a4f5c"
LINE = "#25282f"
BOX = "#1c1e23"
CALL = "#e0682f"
PUT = "#2f8fc0"
FONT = "Roboto Mono, monospace"


# Page setup
st.set_page_config(page_title="GEX Dashboard", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&display=swap');

    html, body, p, label, input, li, h1, h2, h3 {
        font-family: 'Roboto Mono', monospace !important;
    }

    p, label, input, li {
        font-size: 17px !important;
    }

    [data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Rounded' !important;
    }

    .stApp {
        background-color: #131417;
    }

    [data-testid="stSidebar"] {
        background-color: #1c1e23;
    }

    .block-container,
    [data-testid="stMainBlockContainer"] {
        max-width: 100% !important;
        padding: 48px 48px 64px !important;
    }

    h1 {
        font-size: 28px !important;
        font-weight: 500 !important;
        color: #f2f3f5 !important;
    }

    [data-testid="stSidebar"] h3 {
        font-size: 20px !important;
        color: #f2f3f5 !important;
    }

    [data-testid="stSidebar"] label p {
        font-size: 17px !important;
        color: #f2f3f5;
    }

    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        margin-top: 12px;
    }

    [data-testid="stMultiSelect"] span[data-baseweb="tag"],
    [data-baseweb="tag"] {
        background-color: #25282f !important;
        border: 1px solid #4a4f5c;
    }

    [data-baseweb="tag"] span {
        color: #f2f3f5 !important;
        font-size: 16px !important;
    }

    [data-testid="stCaptionContainer"] p {
        font-size: 16px !important;
        color: #8b91a3;
    }

    *:focus-visible {
        outline: 2px solid #ef7a45 !important;
        outline-offset: 2px;
    }

    [data-testid="stMetricLabel"] p {
        font-size: 17px !important;
        color: #8b91a3;
    }

    [data-testid="stMetricValue"] {
        font-size: 36px !important;
        font-weight: 500;
        color: #f2f3f5;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Gamma Exposure (GEX) Dashboard")


# Sidebar settings
st.sidebar.subheader("Settings")

ticker = st.sidebar.text_input(
    "Ticker",
    "SPY",
    help="Stock or ETF symbol, like SPY or QQQ."
).upper()

num_expiries = st.sidebar.slider(
    "How many expiries to load",
    1, 10, 4,
    help="Loads the nearest expiration dates first."
)

use_sample = st.sidebar.checkbox(
    "Use sample data",
    help="Fake data for testing without internet."
)


# Load option data
@st.cache_data(ttl=600)
def load_data(ticker, num_expiries, use_sample):

    if use_sample:
        return make_sample_chain(num_expiries=num_expiries)

    return get_chain(ticker, num_expiries)


try:
    spot, chain = load_data(ticker, num_expiries, use_sample)

except Exception as error:
    st.error(f"Could not load data: {error}")
    st.stop()


# Choose expiration dates
all_expiries = sorted(chain["expiry"].unique())

picked = st.sidebar.multiselect(
    "Expiries",
    all_expiries,
    default=all_expiries,
    help="Pick which expiration dates to include."
)

chain = chain[chain["expiry"].isin(picked)]

if chain.empty:
    st.warning("No option data available.")
    st.stop()


# Calculate GEX
chain = add_gex(chain, spot)

strikes = gex_by_strike(chain)
expiries = gex_by_expiry(chain)

flip = find_gamma_flip(chain, spot)
call_wall, put_wall = find_walls(strikes)

total_gex = chain["gex"].sum()


# Display main numbers
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Spot Price", f"${spot:,.2f}")

if total_gex < 0:
    gex_text = f"-${abs(total_gex) / 1e9:,.2f}B"
else:
    gex_text = f"${total_gex / 1e9:,.2f}B"

col2.metric("Net GEX", gex_text)

if flip is not None:
    flip_text = f"${flip:,.2f}"
else:
    flip_text = "Not found"

col3.metric("Gamma Flip", flip_text)
col4.metric("Call Wall", f"${call_wall:,.0f}")
col5.metric("Put Wall", f"${put_wall:,.0f}")


# Show estimated gamma position
if total_gex > 0:
    dot = CALL
    message = "Positive estimated GEX: hedging may reduce price swings."

elif total_gex < 0:
    dot = PUT
    message = "Negative estimated GEX: hedging may increase price swings."

else:
    dot = FAINT
    message = "Estimated net GEX is zero."

st.markdown(
    f'<p style="font-size:19px !important; margin-top:12px;"><span style="display:inline-block; width:12px; height:12px; '
    f'border-radius:50%; margin-right:8px; background:{dot}"></span>{message}</p>',
    unsafe_allow_html=True
)


def style_chart(fig):

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=18, color=TEXT),
        title_font=dict(size=22, color=STRONG),
        legend=dict(orientation="h", y=1.1, x=0, font=dict(size=18)),
        margin=dict(l=10, r=10, t=110, b=10),
        hoverlabel=dict(bgcolor=BOX, bordercolor=LINE, font=dict(family=FONT, size=18, color=STRONG)),
        barcornerradius=4,
        bargap=0.15
    )

    fig.update_xaxes(gridcolor=LINE, linecolor=LINE, zeroline=False, tickfont=dict(size=17), title_font=dict(size=18))
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=FAINT, tickfont=dict(size=17), title_font=dict(size=18))
    fig.update_annotations(font_size=18)

    return fig


# Chart 1: GEX by strike
low = spot * 0.9
high = spot * 1.1

near = strikes[
    (strikes["strike"] > low) &
    (strikes["strike"] < high)
]

fig = go.Figure()

fig.add_bar(
    x=near["strike"],
    y=near["call_gex"] / 1e6,
    name="Call GEX",
    marker_color=CALL,
    hovertemplate="Strike %{x}<br>Call GEX $%{y:,.1f}M<extra></extra>"
)

fig.add_bar(
    x=near["strike"],
    y=near["put_gex"] / 1e6,
    name="Put GEX",
    marker_color=PUT,
    hovertemplate="Strike %{x}<br>Put GEX $%{y:,.1f}M<extra></extra>"
)

# Mark the current stock price
fig.add_vline(
    x=spot,
    line_dash="dash",
    line_color=STRONG,
    line_width=1,
    annotation_text="Spot",
    annotation_font_color=STRONG,
    annotation_position="top left" if flip is not None and flip > spot else "top right"
)

# Mark the gamma flip
if flip is not None:
    fig.add_vline(
        x=flip,
        line_dash="dot",
        line_color=TEXT,
        line_width=1,
        annotation_text="Flip",
        annotation_position="top right" if flip > spot else "top left"
    )

fig.update_layout(
    title="GEX by Strike",
    height=600,
    barmode="relative",
    xaxis_title="Strike Price",
    yaxis_title="GEX ($ millions per 1% move)"
)

st.plotly_chart(style_chart(fig), use_container_width=True)


# Chart 2: GEX by expiry
colours = [CALL if gex > 0 else PUT for gex in expiries["gex"]]

fig2 = go.Figure()

fig2.add_bar(
    x=expiries["expiry"],
    y=expiries["gex"] / 1e6,
    marker_color=colours,
    hovertemplate="%{x}<br>Net GEX $%{y:,.1f}M<extra></extra>"
)

fig2.update_layout(
    title="Net GEX by Expiry",
    height=450,
    xaxis_title="Expiration Date",
    yaxis_title="GEX ($ millions per 1% move)"
)

fig2.update_xaxes(type="category")

st.plotly_chart(style_chart(fig2), use_container_width=True)


# Data information
if use_sample:
    st.caption("Using sample data for testing.")

st.caption(
    "GEX assumes dealers are long calls and short puts. "
    "Actual dealer positions are unknown. "
    "Open interest may be delayed. "
    "These numbers are estimates, not trading signals."
)

st.markdown(
    f'<p style="font-size:16px; color:{TEXT}; margin-top:40px;">'
    f'© 2026 <a href="https://amandaxuan.com" style="color:{STRONG};">Amanda Xuan</a></p>',
    unsafe_allow_html=True
)