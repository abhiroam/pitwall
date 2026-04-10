import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os, time, random
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

st.set_page_config(page_title="PitWall AI", page_icon="🏎", layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
DRIVER_COLORS = {'HAM': '#00D2BE', 'VER': '#3671C6', 'LEC': '#DC0000', 'NOR': '#FF8000'}
DRIVER_NAMES  = {'HAM': 'Lewis Hamilton', 'VER': 'Max Verstappen', 'LEC': 'Charles Leclerc', 'NOR': 'Lando Norris'}

TYRE_COLORS = {'SOFT': '#e8001d', 'MEDIUM': '#ffc800', 'HARD': '#dddddd', 'INTER': '#00b450', 'WET': '#0082dc'}
TYRE_LIFE   = {'SOFT': 18, 'MEDIUM': 28, 'HARD': 40, 'INTER': 35, 'WET': 50}
TYRE_PACE   = {'SOFT': 0.0, 'MEDIUM': 0.8, 'HARD': 1.6, 'INTER': 2.4, 'WET': 4.0}
TYRE_ALT    = {'SOFT': 'HARD', 'MEDIUM': 'SOFT', 'HARD': 'MEDIUM', 'INTER': 'WET', 'WET': 'INTER'}

CHART_INFO = {
    'AvgThrottle': {'title': 'THROTTLE APPLICATION %',  'unit': '%',    'normal': 'Average throttle % across the lap.',     'anomaly': 'ANOMALY — Throttle pattern differs from baseline.'},
    'AvgSpeed':    {'title': 'AVERAGE SPEED km/h',       'unit': 'km/h', 'normal': 'Average speed across the full lap.',      'anomaly': 'ANOMALY — Speed outside normal range.'},
    'BrakeRatio':  {'title': 'BRAKE RATIO',              'unit': '',     'normal': 'Percentage of lap spent braking.',        'anomaly': 'ANOMALY — Braking behaviour changed from baseline.'},
}

RACES = ['Bahrain GP', 'Saudi Arabian GP', 'Australian GP', 'Japanese GP', 'Chinese GP',
         'Miami GP', 'Emilia Romagna GP', 'Monaco GP', 'Canadian GP', 'Spanish GP',
         'Austrian GP', 'British GP', 'Belgian GP', 'Dutch GP', 'Italian GP']

TOTAL_LAPS = 57

# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@300;400;500;600&family=Share+Tech+Mono&display=swap');
html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }
.stApp { background-color: #15151e; }
section[data-testid="stSidebar"] { display:none !important; }
header[data-testid="stHeader"] { display:none !important; }
.block-container { padding:0 !important; max-width:100% !important; }

.top-nav { position:sticky; top:0; z-index:999; background:#1a1a27; border-bottom:1px solid #38383f;
    display:flex; align-items:center; justify-content:space-between; padding:0 40px; height:60px; }
.nav-logo { font-family:'Barlow Condensed',sans-serif; font-size:26px; font-weight:900;
    letter-spacing:2px; text-transform:uppercase; color:#fff; }
.nav-logo span { color:#e8001d; }
.redbar { height:3px; background:#e8001d; width:100%; }
.dash-content { padding:12px 40px; }

.metric-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:2px; margin-bottom:16px; }
.metric-card { background:#1f1f2e; border:1px solid #38383f; border-top:3px solid #e8001d; padding:16px 20px; }
.metric-label { font-family:'Barlow Condensed',sans-serif; font-size:15px; font-weight:700; color:#ffffff;
    letter-spacing:3px; text-transform:uppercase; margin-bottom:8px; }
.metric-value { font-family:'Barlow Condensed',sans-serif; font-size:52px; font-weight:900; color:#ffffff; line-height:1; }
.metric-value.red { color:#e8001d; }
.metric-value.green { color:#00ff88; }
.metric-sub { font-family:'Barlow Condensed',sans-serif; font-size:13px; color:#959595; margin-top:4px; letter-spacing:1px; }

.sec-header { display:flex; align-items:center; gap:12px; margin:16px 0 12px; padding-bottom:8px; border-bottom:1px solid #38383f; }
.sec-title { font-family:'Barlow Condensed',sans-serif; font-size:24px; font-weight:900; color:#ffffff;
    letter-spacing:3px; text-transform:uppercase; }
.sec-line { flex:1; height:1px; background:linear-gradient(to right,#38383f,transparent); }
.sec-tag { font-family:'Barlow Condensed',sans-serif; font-size:11px; font-weight:700; color:#959595;
    letter-spacing:2px; border:1px solid #38383f; padding:3px 10px; text-transform:uppercase; }

/* Tyre buttons */
.tyre-grid { display:flex; gap:8px; margin-bottom:12px; flex-wrap:wrap; }
.tyre-pill { display:inline-block; font-family:'Barlow Condensed',sans-serif; font-size:13px; font-weight:700;
    letter-spacing:2px; padding:6px 16px; border-radius:2px; cursor:pointer; text-transform:uppercase; border:2px solid; }

/* Pit log */
.pit-log { background:#0f0f0f; border:1px solid #1a1a1a; border-radius:2px; padding:12px 14px;
    font-family:'Share Tech Mono',monospace; font-size:12px; color:#666; max-height:200px; overflow-y:auto; }
.pit-entry { padding:2px 0; border-bottom:1px solid #111; }
.pit-entry.ok  { color:#00d2be; }
.pit-entry.warn { color:#ff8800; }
.pit-entry.crit { color:#e8001d; }

.pit-panel { background:#1a1a27; border:1px solid #38383f; border-radius:2px; padding:16px 18px; margin-bottom:10px; }
.pit-panel.red   { border-left:3px solid #e8001d; }
.pit-panel.teal  { border-left:3px solid #00d2be; }
.pit-panel.amber { border-left:3px solid #ffc800; }
.pit-panel-title { font-family:'Barlow Condensed',sans-serif; font-size:13px; font-weight:700;
    letter-spacing:3px; text-transform:uppercase; margin-bottom:10px; }

.anom-card { background:#1f1f2e; border:1px solid #38383f; border-left:3px solid #e8001d;
    padding:14px 18px; margin-bottom:6px; display:flex; align-items:center; gap:14px; }
.anom-lap { font-family:'Barlow Condensed',sans-serif; font-size:32px; font-weight:900; color:#fff;
    min-width:56px; line-height:1; }
.anom-info { flex:1; }
.anom-detail { font-family:'Barlow',sans-serif; font-size:13px; color:#959595; margin-top:4px; }
.sev-bar { height:3px; background:#38383f; border-radius:2px; overflow:hidden; margin-top:6px; }
.sev-fill { height:100%; background:#e8001d; }

div.stButton > button {
    font-family:'Barlow Condensed',sans-serif !important; font-size:14px !important;
    font-weight:700 !important; letter-spacing:2px !important; text-transform:uppercase !important;
    background:#1a1a27 !important; color:#959595 !important; border:none !important;
    border-bottom:3px solid transparent !important; border-radius:0 !important;
    padding:12px 4px !important; transition:all 0.2s !important; }
div.stButton > button:hover { color:#fff !important; border-bottom:3px solid #38383f !important; }
div.stButton > button:focus { color:#fff !important; border-bottom:3px solid #e8001d !important; box-shadow:none !important; }

.stSelectbox label { font-family:'Barlow Condensed',sans-serif !important; font-size:16px !important;
    font-weight:700 !important; color:#ffffff !important; letter-spacing:3px !important; text-transform:uppercase !important; }
.stSelectbox > div > div { background:#1f1f2e !important; border:1px solid #38383f !important;
    color:#ffffff !important; border-radius:2px !important; font-family:'Barlow Condensed',sans-serif !important;
    font-size:16px !important; font-weight:700 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    tel  = pd.read_csv('data/telemetry_raw.csv')     if os.path.exists('data/telemetry_raw.csv')     else pd.DataFrame()
    anom = pd.read_csv('outputs/anomaly_report.csv') if os.path.exists('outputs/anomaly_report.csv') else pd.DataFrame()
    rad  = pd.read_csv('outputs/radio_messages.csv') if os.path.exists('outputs/radio_messages.csv') else pd.DataFrame()
    return tel, anom, rad

tel_df, anom_df, radio_df = load_data()

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
defaults = {
    'page':         'DNA FINGERPRINT',
    'pit_tyre':     'SOFT',
    'pit_history':  [],
    'pit_log':      ['[SYSTEM] PitWall AI ready.'],
    'pit_running':  False,
    'pit_lap':      20,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# NAV
# ─────────────────────────────────────────────
st.markdown("""
<div class="redbar"></div>
<div class="top-nav">
    <div class="nav-logo">Pit<span>Wall</span> AI</div>
</div>
""", unsafe_allow_html=True)

PAGES = ['DNA FINGERPRINT', 'VS COMPARISON', 'ANOMALY TIMELINE', 'FASTEST LAP',
         'AI RADIO FEED', 'PIT STOP SIM', 'EXPORT REPORT', 'F1 NEWS']

page_cols = st.columns(len(PAGES))
for i, page in enumerate(PAGES):
    with page_cols[i]:
        if st.button(page, key=f'btn_{i}', use_container_width=True):
            st.session_state.page = page

current_page = st.session_state.page
st.markdown('<div class="dash-content">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GLOBAL SELECTORS
# ─────────────────────────────────────────────
drivers_avail = tel_df['Driver'].unique().tolist() if not tel_df.empty else list(DRIVER_COLORS.keys())
races_avail   = tel_df['Race'].unique().tolist()   if not tel_df.empty else RACES

sel_col1, sel_col2, sel_col3, sel_col4 = st.columns([2, 2, 2, 2])
with sel_col1:
    sel_driver = st.selectbox("DRIVER", drivers_avail,
        format_func=lambda d: f"{d} — {DRIVER_NAMES.get(d, d)}")
with sel_col2:
    sel_race = st.selectbox("RACE", races_avail) if races_avail else None
with sel_col3:
    compare_drivers = [d for d in drivers_avail if d != sel_driver]
    compare_driver  = st.selectbox("COMPARE WITH", ['None'] + compare_drivers)
with sel_col4:
    sel_lap = st.slider("LAP", min_value=1, max_value=TOTAL_LAPS, value=1, key='lap_slider')

dcolor = DRIVER_COLORS.get(sel_driver, '#E8001D')
dname  = DRIVER_NAMES.get(sel_driver, sel_driver)

# ─────────────────────────────────────────────
# METRICS STRIP
# ─────────────────────────────────────────────
if not anom_df.empty:
    d_anom = anom_df[anom_df['Driver'] == sel_driver]
    d_tel  = tel_df[tel_df['Driver'] == sel_driver]
    total  = len(d_tel)
    anoms  = len(d_anom)
    pct    = round(anoms / total * 100, 1) if total else 0
    spd    = round(d_tel['AvgSpeed'].mean(), 1) if not d_tel.empty else 0
    thr    = round(d_tel['AvgThrottle'].mean(), 1) if not d_tel.empty else 0
    st.markdown(f"""
    <div style="margin:8px 0 6px;font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:700;
        color:#ffffff;letter-spacing:3px;">{sel_driver} &nbsp;<span style='color:#555'>·</span>&nbsp;
        {dname} &nbsp;<span style='color:#555'>·</span>&nbsp; 2024 SEASON</div>
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-label">Laps Analyzed</div>
            <div class="metric-value">{total}</div><div class="metric-sub">Across all races</div></div>
        <div class="metric-card"><div class="metric-label">Anomalies</div>
            <div class="metric-value red">{anoms}</div><div class="metric-sub">{pct}% of laps flagged</div></div>
        <div class="metric-card"><div class="metric-label">Avg Speed</div>
            <div class="metric-value">{spd}</div><div class="metric-sub">km/h</div></div>
        <div class="metric-card"><div class="metric-label">Avg Throttle</div>
            <div class="metric-value">{thr}<span style="font-size:18px;color:#555">%</span></div>
            <div class="metric-sub">Aggression index</div></div>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def dark_fig():
    return dict(plot_bgcolor='#0f0f0f', paper_bgcolor='#080808',
                font=dict(color='#cccccc', family='monospace'),
                hoverlabel=dict(bgcolor='#111', bordercolor='#333',
                                font=dict(color='#fff', size=12, family='monospace')))

def dark_axes():
    return (dict(title='Lap Number', gridcolor='#2e2e40', color='#cccccc',
                 showline=True, linecolor='#2e2e40'),
            dict(gridcolor='#2e2e40', color='#cccccc', showline=True, linecolor='#2e2e40'))

def tyre_badge(compound):
    c = TYRE_COLORS.get(compound, '#888')
    return (f'<span style="background:rgba(0,0,0,0);border:1px solid {c};color:{c};'
            f'font-family:Barlow Condensed,sans-serif;font-size:12px;font-weight:700;'
            f'padding:2px 8px;letter-spacing:1px;">{compound}</span>')


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DNA FINGERPRINT
# ─────────────────────────────────────────────────────────────────────────────
if current_page == "DNA FINGERPRINT":
    st.markdown('<div class="sec-header"><div class="sec-title">Telemetry DNA</div>'
                '<div class="sec-line"></div><div class="sec-tag">HOVER FOR INSIGHTS</div></div>',
                unsafe_allow_html=True)

    if not tel_df.empty and sel_race:
        race_data = tel_df[(tel_df['Driver'] == sel_driver) & (tel_df['Race'] == sel_race)].copy()
        if not anom_df.empty:
            a_laps = set(anom_df[(anom_df['Driver'] == sel_driver) &
                                  (anom_df['Race'] == sel_race)]['LapNumber'].tolist())
            race_data['IsAnomaly'] = race_data['LapNumber'].isin(a_laps)
        else:
            race_data['IsAnomaly'] = False

        # Lap scrubber — highlight current lap
        if not race_data.empty:
            norm = race_data[~race_data['IsAnomaly']]
            anom = race_data[race_data['IsAnomaly']]
            for col, info in CHART_INFO.items():
                fig = go.Figure()
                # Baseline area
                fig.add_trace(go.Scatter(
                    x=norm['LapNumber'], y=norm[col], mode='lines+markers',
                    name=f'{sel_driver} baseline',
                    line=dict(color=dcolor, width=2.5), marker=dict(size=5, color=dcolor),
                    fill='tozeroy',
                    fillcolor=f'rgba({int(dcolor[1:3],16)},{int(dcolor[3:5],16)},{int(dcolor[5:7],16)},0.06)',
                    hovertemplate=f'<b>LAP %{{x}}</b><br>{info["title"]}: <b>%{{y:.2f}}{info["unit"]}</b>'
                                  f'<br><span style="color:#aaa;font-size:11px">{info["normal"]}</span><extra></extra>'))
                # Anomaly markers
                if not anom.empty:
                    fig.add_trace(go.Scatter(
                        x=anom['LapNumber'], y=anom[col], mode='markers', name='Anomaly',
                        marker=dict(size=14, color='#E8001D', symbol='triangle-down',
                                    line=dict(color='#ff8888', width=1.5)),
                        hovertemplate=f'<b>⚠ ANOMALY — LAP %{{x}}</b><br>{info["title"]}: '
                                      f'<b>%{{y:.2f}}{info["unit"]}</b><br>'
                                      f'<span style="color:#ff6666;font-size:11px">{info["anomaly"]}</span><extra></extra>'))
                # Current lap vline
                fig.add_vline(x=sel_lap, line_color='#ffffff', line_dash='dot', line_width=1,
                              annotation_text=f'Lap {sel_lap}',
                              annotation_font_color='#ffffff', annotation_font_size=10)

                xax, yax = dark_axes()
                fig.update_layout(title=dict(
                    text=f'{info["title"]}  <span style="font-size:11px;color:#444">— {sel_driver} · {sel_race} 2024</span>',
                    font=dict(size=13, color='#ffffff', family='monospace'), x=0),
                    height=260, margin=dict(l=60, r=20, t=44, b=36),
                    legend=dict(bgcolor='#111', bordercolor='#222', borderwidth=1,
                                font=dict(color='#ccc', size=10)),
                    xaxis=xax, yaxis=yax, hovermode='x unified', **dark_fig())
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Select a driver and race, or load telemetry data.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — VS COMPARISON
# ─────────────────────────────────────────────────────────────────────────────
if current_page == "VS COMPARISON":
    st.markdown('<div class="sec-header"><div class="sec-title">Driver vs Driver</div>'
                '<div class="sec-line"></div><div class="sec-tag">HEAD TO HEAD</div></div>',
                unsafe_allow_html=True)

    if compare_driver != 'None' and sel_race and not tel_df.empty:
        d1     = tel_df[(tel_df['Driver'] == sel_driver)    & (tel_df['Race'] == sel_race)]
        d2     = tel_df[(tel_df['Driver'] == compare_driver) & (tel_df['Race'] == sel_race)]
        c2color = DRIVER_COLORS.get(compare_driver, '#888888')

        for col, info in CHART_INFO.items():
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=d1['LapNumber'], y=d1[col], mode='lines+markers', name=sel_driver,
                line=dict(color=dcolor, width=2.5), marker=dict(size=5),
                hovertemplate=f'<b>{sel_driver} LAP %{{x}}</b><br>{info["title"]}: <b>%{{y:.2f}}{info["unit"]}</b><extra></extra>'))
            fig.add_trace(go.Scatter(
                x=d2['LapNumber'], y=d2[col], mode='lines+markers', name=compare_driver,
                line=dict(color=c2color, width=2.5, dash='dot'), marker=dict(size=5),
                hovertemplate=f'<b>{compare_driver} LAP %{{x}}</b><br>{info["title"]}: <b>%{{y:.2f}}{info["unit"]}</b><extra></extra>'))
            fig.add_vline(x=sel_lap, line_color='#ffffff', line_dash='dot', line_width=1,
                          annotation_text=f'Lap {sel_lap}', annotation_font_color='#fff', annotation_font_size=10)

            xax, yax = dark_axes()
            fig.update_layout(
                title=dict(text=f'{info["title"]}  <span style="font-size:11px;color:#444">— {sel_driver} vs {compare_driver} · {sel_race}</span>',
                           font=dict(size=13, color='#ffffff', family='monospace'), x=0),
                height=260, margin=dict(l=60, r=20, t=44, b=36),
                legend=dict(bgcolor='#111', bordercolor='#222', borderwidth=1, font=dict(color='#ccc', size=10)),
                xaxis=xax, yaxis=yax, hovermode='x unified', **dark_fig())
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # Head-to-head stat cards
        st.markdown('<div class="sec-header"><div class="sec-title">Head to Head Stats</div>'
                    '<div class="sec-line"></div></div>', unsafe_allow_html=True)
        stat_cols = st.columns(3)
        metrics = [('AvgSpeed', 'Avg Speed', 'km/h'), ('AvgThrottle', 'Avg Throttle', '%'), ('BrakeRatio', 'Brake Ratio', '')]
        for i, (mc, label, unit) in enumerate(metrics):
            v1 = round(d1[mc].mean(), 2) if not d1.empty else 0
            v2 = round(d2[mc].mean(), 2) if not d2.empty else 0
            stat_cols[i].metric(label, f"{v1}{unit}", f"{round(v1-v2,2)}{unit} vs {compare_driver}")
    else:
        st.info("Select a driver in 'COMPARE WITH' to enable head-to-head view.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — ANOMALY TIMELINE
# ─────────────────────────────────────────────────────────────────────────────
if current_page == "ANOMALY TIMELINE":
    st.markdown('<div class="sec-header"><div class="sec-title">Anomaly Timeline</div>'
                '<div class="sec-line"></div><div class="sec-tag">RACE HEARTBEAT</div></div>',
                unsafe_allow_html=True)

    if not anom_df.empty and not tel_df.empty and sel_race:
        race_data = tel_df[(tel_df['Driver'] == sel_driver) & (tel_df['Race'] == sel_race)].copy()
        race_anom = anom_df[(anom_df['Driver'] == sel_driver) & (anom_df['Race'] == sel_race)].copy()

        if not race_data.empty:
            race_data['Severity'] = 0.0
            for _, row in race_anom.iterrows():
                sev = round((1 - row['SeverityScore']) * 100, 1)
                race_data.loc[race_data['LapNumber'] == row['LapNumber'], 'Severity'] = sev

            fig = go.Figure()
            fig.add_trace(go.Bar(x=race_data['LapNumber'], y=[100]*len(race_data),
                                 marker_color='#111111', name='Normal lap',
                                 hovertemplate='LAP %{x} — Normal<extra></extra>'))
            anom_data = race_data[race_data['Severity'] > 0]
            fig.add_trace(go.Bar(
                x=anom_data['LapNumber'], y=anom_data['Severity'], name='Anomaly severity',
                marker=dict(color=anom_data['Severity'],
                            colorscale=[[0, '#ff8800'], [1, '#E8001D']], showscale=True,
                            colorbar=dict(title=dict(text='Severity %', font=dict(color='#888')),
                                          tickfont=dict(color='#888'))),
                hovertemplate='<b>⚠ LAP %{x}</b><br>Severity: <b>%{y:.1f}%</b><extra></extra>'))
            fig.add_vline(x=sel_lap, line_color='#ffffff', line_dash='dot', line_width=1,
                          annotation_text=f'Lap {sel_lap}', annotation_font_color='#fff', annotation_font_size=10)
            fig.update_layout(
                title=dict(text=f'Race Anomaly Timeline — {sel_driver} · {sel_race} 2024',
                           font=dict(size=13, color='#ffffff', family='monospace'), x=0),
                barmode='overlay', height=320, margin=dict(l=60, r=60, t=50, b=40),
                xaxis=dict(title='Lap Number', gridcolor='#2e2e40', color='#cccccc'),
                yaxis=dict(title='Anomaly Severity %', gridcolor='#2e2e40', color='#cccccc', range=[0, 105]),
                legend=dict(bgcolor='#111', bordercolor='#222', font=dict(color='#ccc', size=10)),
                **dark_fig())
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            # Anomaly cards
            if not race_anom.empty:
                for _, row in race_anom.sort_values('SeverityScore').iterrows():
                    sev = round((1 - row['SeverityScore']) * 100, 1)
                    st.markdown(f"""
                    <div class="anom-card">
                        <div class="anom-lap">{int(row['LapNumber'])}<span style="font-size:11px;color:#555;display:block;font-family:'Barlow Condensed';letter-spacing:2px;">LAP</span></div>
                        <div class="anom-info">
                            <div style="font-family:'Barlow Condensed';font-size:16px;font-weight:700;letter-spacing:1px;">
                                {sel_driver} · {tyre_badge(row['Compound'])} · {row['Race']}</div>
                            <div class="anom-detail">Lap time: {round(row['LapTime_s'],3)}s &nbsp;·&nbsp; {sev}% deviation</div>
                            <div class="sev-bar"><div class="sev-fill" style="width:{sev}%"></div></div>
                        </div>
                        <div style="font-family:'Barlow Condensed';font-size:22px;font-weight:900;color:#e8001d;min-width:60px;text-align:right;">{sev}%</div>
                    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — FASTEST LAP
# ─────────────────────────────────────────────────────────────────────────────
if current_page == "FASTEST LAP":
    st.markdown('<div class="sec-header"><div class="sec-title">Fastest Lap Analysis</div>'
                '<div class="sec-line"></div><div class="sec-tag">PEAK PERFORMANCE</div></div>',
                unsafe_allow_html=True)

    if not tel_df.empty and sel_race:
        race_data = tel_df[(tel_df['Driver'] == sel_driver) & (tel_df['Race'] == sel_race)].copy().dropna(subset=['LapTime_s'])
        if not race_data.empty:
            fastest  = race_data.loc[race_data['LapTime_s'].idxmin()]
            slowest  = race_data.loc[race_data['LapTime_s'].idxmax()]
            avg_time = race_data['LapTime_s'].mean()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="metric-card" style="border-left:3px solid #00ff88;border-top:none;">
                    <div class="metric-label" style="color:#00ff88;">Fastest Lap</div>
                    <div class="metric-value green" style="font-size:32px;">
                        {int(fastest['LapTime_s']//60)}:{fastest['LapTime_s']%60:06.3f}</div>
                    <div class="metric-sub">LAP {int(fastest['LapNumber'])} · {fastest['Compound']}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Average Lap</div>
                    <div class="metric-value" style="font-size:28px;">
                        {int(avg_time//60)}:{avg_time%60:06.3f}</div>
                    <div class="metric-sub">Over {len(race_data)} laps</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                delta = round(slowest['LapTime_s'] - fastest['LapTime_s'], 3)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Lap Time Variance</div>
                    <div class="metric-value red">+{delta}s</div>
                    <div class="metric-sub">Fastest vs slowest</div>
                </div>""", unsafe_allow_html=True)

            # Lap time chart
            fig = go.Figure()
            if not anom_df.empty:
                a_laps = set(anom_df[(anom_df['Driver'] == sel_driver) &
                                      (anom_df['Race'] == sel_race)]['LapNumber'].tolist())
                race_data['IsAnomaly'] = race_data['LapNumber'].isin(a_laps)
            else:
                race_data['IsAnomaly'] = False

            norm = race_data[~race_data['IsAnomaly']]
            anom = race_data[race_data['IsAnomaly']]

            fig.add_trace(go.Scatter(
                x=norm['LapNumber'], y=norm['LapTime_s'], mode='lines+markers', name='Lap time',
                line=dict(color=dcolor, width=2), marker=dict(size=5),
                hovertemplate='LAP %{x}<br>Time: <b>%{y:.3f}s</b><extra></extra>'))
            if not anom.empty:
                fig.add_trace(go.Scatter(
                    x=anom['LapNumber'], y=anom['LapTime_s'], mode='markers', name='Anomaly lap',
                    marker=dict(size=12, color='#E8001D', symbol='triangle-down'),
                    hovertemplate='⚠ ANOMALY LAP %{x}<br>Time: <b>%{y:.3f}s</b><extra></extra>'))
            fig.add_vline(x=fastest['LapNumber'], line_color='#00ff88', line_dash='dash', line_width=1,
                          annotation_text='Fastest', annotation_font_color='#00ff88', annotation_font_size=10)
            fig.add_vline(x=sel_lap, line_color='#ffffff', line_dash='dot', line_width=1,
                          annotation_text=f'Lap {sel_lap}', annotation_font_color='#fff', annotation_font_size=10)
            fig.update_layout(
                title=dict(text=f'LAP TIMES — {sel_driver} · {sel_race} 2024',
                           font=dict(size=13, color='#ffffff', family='monospace'), x=0),
                height=280, margin=dict(l=60, r=20, t=44, b=36),
                xaxis=dict(title='Lap Number', gridcolor='#2e2e40', color='#cccccc'),
                yaxis=dict(title='Lap Time (s)', gridcolor='#2e2e40', color='#cccccc'),
                legend=dict(bgcolor='#111', bordercolor='#222', font=dict(color='#ccc', size=10)),
                **dark_fig())
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — AI RADIO FEED
# ─────────────────────────────────────────────────────────────────────────────
if current_page == "AI RADIO FEED":
    st.markdown('<div class="sec-header"><div class="sec-title">Team Radio Feed</div>'
                '<div class="sec-line"></div><div class="sec-tag">GROQ / LLAMA 3.3</div></div>',
                unsafe_allow_html=True)

    if not radio_df.empty:
        driver_radio = radio_df[radio_df['Driver'] == sel_driver].sort_values('LapNumber')
        if not driver_radio.empty:
            if sel_race and sel_race in driver_radio['Race'].values:
                driver_radio = driver_radio[driver_radio['Race'] == sel_race]
            for _, row in driver_radio.iterrows():
                sev = row['Severity']
                urgency = "CRITICAL" if sev > 80 else "WARNING" if sev > 50 else "INFO"
                uc = "#E8001D" if sev > 80 else "#ff8800" if sev > 50 else "#00D2BE"
                st.markdown(f"""
                <div style="background:#1f1f2e;border:1px solid #38383f;border-left:3px solid {uc};
                    padding:18px 22px;margin-bottom:10px;border-radius:2px;">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                        <div style="width:8px;height:8px;background:{uc};border-radius:50%;"></div>
                        <div style="font-family:'Barlow Condensed';font-size:13px;font-weight:700;
                            color:#959595;letter-spacing:2px;text-transform:uppercase;">
                            {urgency} · LAP {int(row['LapNumber'])} · {row['Race'].upper()} · {row['Compound']} TIRES</div>
                    </div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:9px;color:#333;
                        margin-bottom:8px;letter-spacing:2px;">{sev}% DEVIATION FROM BASELINE</div>
                    <div style="font-family:'Barlow',sans-serif;font-size:16px;color:#ffffff;line-height:1.8;
                        padding:14px 18px;background:#15151e;border:1px solid #38383f;border-radius:2px;">
                        {str(row['RadioMsg'])}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No radio messages for this driver.")
    else:
        st.info("Run 3_ai_copilot.py first to generate radio messages.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — PIT STOP SIMULATOR  ← NEW INTERACTIVE PAGE
# ─────────────────────────────────────────────────────────────────────────────
if current_page == "PIT STOP SIM":
    st.markdown('<div class="sec-header"><div class="sec-title">Pit Stop Simulator</div>'
                '<div class="sec-line"></div><div class="sec-tag">INTERACTIVE</div></div>',
                unsafe_allow_html=True)

    left, right = st.columns([1, 1])

    with left:
        # ── Tyre Selection ──
        st.markdown('<div class="pit-panel red"><div class="pit-panel-title" style="color:#e8001d;">Tyre Selection</div>', unsafe_allow_html=True)
        tyre_cols = st.columns(5)
        tyre_compounds = ['SOFT', 'MEDIUM', 'HARD', 'INTER', 'WET']
        for i, comp in enumerate(tyre_compounds):
            with tyre_cols[i]:
                tc = TYRE_COLORS[comp]
                label = f"{'🔴' if comp=='SOFT' else '🟡' if comp=='MEDIUM' else '⚪' if comp=='HARD' else '🟢' if comp=='INTER' else '🔵'} {comp}"
                if st.button(label, key=f'tyre_{comp}', use_container_width=True):
                    st.session_state.pit_tyre = comp
                    st.session_state.pit_log.insert(0, f'[RADIO] Tyre change → {comp} compound requested')
        sel_tyre = st.session_state.pit_tyre
        tc = TYRE_COLORS[sel_tyre]
        st.markdown(f"""<div style="text-align:center;padding:8px 0;font-family:'Barlow Condensed';
            font-size:28px;font-weight:900;color:{tc};letter-spacing:4px;border:2px solid {tc};
            border-radius:2px;margin:8px 0;">{sel_tyre}</div>
            <div style="font-size:11px;color:#555;text-align:center;letter-spacing:2px;">
            MAX LIFE: {TYRE_LIFE[sel_tyre]} LAPS &nbsp;·&nbsp; PACE DELTA: +{TYRE_PACE[sel_tyre]}s</div>
            </div>""", unsafe_allow_html=True)

        # ── Pit Lap Slider ──
        st.markdown('<div class="pit-panel teal" style="margin-top:10px;">'
                    '<div class="pit-panel-title" style="color:#00d2be;">Pit Window</div>',
                    unsafe_allow_html=True)
        pit_lap = st.slider("PIT LAP", min_value=1, max_value=TOTAL_LAPS - 1,
                            value=st.session_state.pit_lap, key='pit_lap_slider')
        st.session_state.pit_lap = pit_lap

        stint1 = pit_lap
        stint2 = TOTAL_LAPS - pit_lap
        alt_tyre = TYRE_ALT[sel_tyre]
        est_loss = round(TYRE_PACE[sel_tyre] * stint1 + TYRE_PACE[alt_tyre] * stint2, 1)

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;">
            <div style="background:#111;padding:10px;border-radius:2px;">
                <div style="font-size:10px;color:#555;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Stint 1</div>
                <div style="font-size:18px;font-weight:900;color:{TYRE_COLORS[sel_tyre]};">Laps 1–{pit_lap}</div>
                <div style="font-size:11px;color:#555;">{sel_tyre}</div>
            </div>
            <div style="background:#111;padding:10px;border-radius:2px;">
                <div style="font-size:10px;color:#555;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Stint 2</div>
                <div style="font-size:18px;font-weight:900;color:{TYRE_COLORS.get(alt_tyre,'#888')};">Laps {pit_lap+1}–{TOTAL_LAPS}</div>
                <div style="font-size:11px;color:#555;">{alt_tyre}</div>
            </div>
        </div>
        <div style="margin-top:8px;font-size:11px;color:#444;letter-spacing:1px;">
            EST. TIME COST {est_loss}s · {len(st.session_state.pit_history)} PIT STOP(S) THIS RACE</div>
        </div>""", unsafe_allow_html=True)

        # ── Execute Button ──
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔴  BOX BOX BOX — EXECUTE PIT STOP", key='exec_pit', use_container_width=True, type='primary'):
            stop_time = round(random.uniform(2.1, 3.8), 2)
            st.session_state.pit_history.append({
                'lap': pit_lap, 'tyre': sel_tyre, 'time': stop_time,
                'stint1': stint1, 'stint2': stint2
            })
            log = st.session_state.pit_log
            log.insert(0, f'[GO] Pit stop complete — {stop_time}s')
            log.insert(0, f'[CREW] New {sel_tyre} tyres fitted')
            log.insert(0, f'[CREW] Wheels off — changing compound')
            log.insert(0, f'[RADIO] BOX BOX BOX — Lap {pit_lap}')
            st.session_state.pit_log = log[:30]
            st.rerun()

    with right:
        # ── Race Engineer Radio Log ──
        st.markdown('<div class="pit-panel teal"><div class="pit-panel-title" style="color:#00d2be;">Race Engineer Feed</div>',
                    unsafe_allow_html=True)
        log_html = ''
        for entry in st.session_state.pit_log:
            cls = 'crit' if 'BOX' in entry or 'CRITICAL' in entry else \
                  'warn' if 'WARN' in entry or 'changing' in entry else \
                  'ok'   if 'complete' in entry or 'fitted' in entry else ''
            log_html += f'<div class="pit-entry {cls}">{entry}</div>'
        st.markdown(f'<div class="pit-log">{log_html}</div></div>', unsafe_allow_html=True)

        # ── Pit Stop History ──
        if st.session_state.pit_history:
            st.markdown('<div class="pit-panel amber" style="margin-top:10px;">'
                        '<div class="pit-panel-title" style="color:#ffc800;">Pit Stop History</div>',
                        unsafe_allow_html=True)
            for i, ps in enumerate(st.session_state.pit_history):
                tc2 = TYRE_COLORS.get(ps['tyre'], '#888')
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;
                    background:#111;border-left:2px solid {tc2};margin-bottom:4px;border-radius:0 2px 2px 0;">
                    <div style="font-size:18px;font-weight:900;min-width:28px;color:#555;">P{i+1}</div>
                    <div style="flex:1;">
                        <div style="font-size:13px;font-weight:700;color:{tc2};">LAP {ps['lap']} → {ps['tyre']}</div>
                        <div style="font-size:10px;color:#555;">
                            Stint {ps['stint1']} + {ps['stint2']} laps</div>
                    </div>
                    <div style="font-size:16px;font-weight:900;color:#00ff88;">{ps['time']}s</div>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("CLEAR PIT HISTORY", key='clear_pit'):
                st.session_state.pit_history = []
                st.session_state.pit_log = ['[SYSTEM] History cleared.']
                st.rerun()

        # ── Tyre Wear Visualisation ──
        st.markdown('<div class="pit-panel" style="margin-top:10px;border-left:3px solid #555;">'
                    '<div class="pit-panel-title" style="color:#aaa;">Tyre Wear Estimate</div>',
                    unsafe_allow_html=True)
        wear_pct = min(100, round(pit_lap / TYRE_LIFE[sel_tyre] * 100))
        wear_color = '#00ff88' if wear_pct < 50 else '#ffc800' if wear_pct < 80 else '#e8001d'
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="font-size:32px;font-weight:900;color:{wear_color};">{wear_pct}%</div>
            <div style="flex:1;">
                <div style="height:8px;background:#222;border-radius:4px;overflow:hidden;">
                    <div style="width:{wear_pct}%;height:100%;background:{wear_color};border-radius:4px;"></div>
                </div>
                <div style="font-size:10px;color:#555;margin-top:4px;letter-spacing:1px;">
                    {'WORN — PIT NOW' if wear_pct > 80 else 'DEGRADING' if wear_pct > 50 else 'GOOD CONDITION'}</div>
            </div>
        </div></div>""", unsafe_allow_html=True)

    # ── Strategy Chart ──
    st.markdown('<div class="sec-header" style="margin-top:16px;"><div class="sec-title">Strategy Overview</div>'
                '<div class="sec-line"></div></div>', unsafe_allow_html=True)

    fig = go.Figure()
    # Stint bars
    fig.add_trace(go.Bar(
        x=[stint1], y=['Race'], name=sel_tyre, orientation='h',
        marker_color=TYRE_COLORS[sel_tyre], width=0.4,
        hovertemplate=f'Stint 1 — {sel_tyre}<br>{stint1} laps<extra></extra>'))
    fig.add_trace(go.Bar(
        x=[stint2], y=['Race'], name=alt_tyre, orientation='h',
        marker_color=TYRE_COLORS.get(alt_tyre, '#888'), width=0.4,
        hovertemplate=f'Stint 2 — {alt_tyre}<br>{stint2} laps<extra></extra>'))
    # Pit window line
    fig.add_vline(x=pit_lap, line_color='#fff', line_dash='dot', line_width=2,
                  annotation_text=f'PIT LAP {pit_lap}', annotation_font_color='#fff',
                  annotation_font_size=11, annotation_position='top')
    fig.update_layout(
        barmode='stack', height=130, margin=dict(l=10, r=20, t=30, b=20),
        xaxis=dict(range=[0, TOTAL_LAPS], gridcolor='#2e2e40', color='#666',
                   title=dict(text='Lap', font=dict(color='#555', size=10))),
        yaxis=dict(gridcolor='#2e2e40', color='#666'),
        legend=dict(bgcolor='#111', bordercolor='#222', font=dict(color='#ccc', size=10),
                    orientation='h', yanchor='bottom', y=1.02),
        **dark_fig())
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — EXPORT REPORT
# ─────────────────────────────────────────────────────────────────────────────
if current_page == "EXPORT REPORT":
    st.markdown('<div class="sec-header"><div class="sec-title">Export Report</div>'
                '<div class="sec-line"></div><div class="sec-tag">PDF</div></div>',
                unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-family:'Barlow',sans-serif;font-size:15px;color:#aaa;margin-bottom:24px;line-height:1.8;">
        Generate a complete anomaly report for <strong style="color:#fff">{dname} ({sel_driver})</strong>
        including all flagged laps, severity scores, tire data and AI radio messages.
    </div>""", unsafe_allow_html=True)

    if st.button("GENERATE PDF REPORT", type="primary"):
        buffer = BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                   leftMargin=20*mm, rightMargin=20*mm,
                                   topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        story  = []

        title_style = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=24,
                                      textColor=colors.HexColor('#E8001D'), spaceAfter=6)
        sub_style   = ParagraphStyle('sub', fontName='Helvetica', fontSize=10,
                                      textColor=colors.HexColor('#888888'), spaceAfter=16)
        h2_style    = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=14,
                                      textColor=colors.black, spaceAfter=8, spaceBefore=16)
        body_style  = ParagraphStyle('body', fontName='Helvetica', fontSize=10,
                                      textColor=colors.HexColor('#333333'), spaceAfter=6, leading=14)

        story.append(Paragraph("PITWALL AI", title_style))
        story.append(Paragraph(f"Anomaly Report — {dname} ({sel_driver}) — 2024 Season", sub_style))
        story.append(Spacer(1, 8*mm))

        if not anom_df.empty:
            d_anom = anom_df[anom_df['Driver'] == sel_driver]
            d_tel  = tel_df[tel_df['Driver'] == sel_driver]
            story.append(Paragraph("Season Summary", h2_style))
            summary_data = [
                ['Metric', 'Value'],
                ['Total laps analyzed', str(len(d_tel))],
                ['Anomalies detected', str(len(d_anom))],
                ['Anomaly rate', f"{round(len(d_anom)/len(d_tel)*100,1)}%" if len(d_tel) else "0%"],
                ['Avg speed', f"{round(d_tel['AvgSpeed'].mean(),1)} km/h"],
                ['Avg throttle', f"{round(d_tel['AvgThrottle'].mean(),1)}%"],
            ]
            t = Table(summary_data, colWidths=[80*mm, 80*mm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8001D')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f9f9f9'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#dddddd')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 8*mm))
            story.append(Paragraph("Generated by PitWall AI — FastF1 · scikit-learn · Groq",
                                    ParagraphStyle('footer', fontName='Helvetica', fontSize=8,
                                                   textColor=colors.HexColor('#aaaaaa'))))

        doc.build(story)
        buffer.seek(0)
        st.download_button(
            label=f"DOWNLOAD {sel_driver} REPORT PDF",
            data=buffer,
            file_name=f"pitwall_ai_{sel_driver}_report.pdf",
            mime="application/pdf"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 8 — F1 NEWS
# ─────────────────────────────────────────────────────────────────────────────
if current_page == "F1 NEWS":
    st.markdown('<div class="sec-header"><div class="sec-title">F1 2026 Upcoming Races</div><div class="sec-line"></div><div class="sec-tag">LIVE</div></div>', unsafe_allow_html=True)

    st.markdown('''
    <div style="text-align:center;padding:40px 20px;">
        <div style="font-size:48px;margin-bottom:16px;">🏁</div>
        <div style="font-family:Barlow Condensed,sans-serif;font-size:32px;font-weight:900;color:#ffffff;letter-spacing:-1px;margin-bottom:8px;">2025 SEASON COMPLETE</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:12px;color:#555;letter-spacing:4px;text-transform:uppercase;margin-bottom:32px;">Abu Dhabi was the final race · December 7, 2025</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:11px;color:#E8001D;letter-spacing:4px;text-transform:uppercase;">No upcoming races — 2026 calendar not yet announced</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('<div class="sec-header"><div class="sec-title">2025 Season Results</div><div class="sec-line"></div><div class="sec-tag">COMPLETED</div></div>', unsafe_allow_html=True)

    races_2025 = [
        {"round": 1,  "race": "Australian GP",    "date": "Mar 16",  "winner": "Norris",     "team": "McLaren",   "flag": "🇦🇺"},
        {"round": 2,  "race": "Chinese GP",        "date": "Mar 23",  "winner": "Piastri",    "team": "McLaren",   "flag": "🇨🇳"},
        {"round": 3,  "race": "Japanese GP",       "date": "Apr 6",   "winner": "Verstappen", "team": "Red Bull",  "flag": "🇯🇵"},
        {"round": 4,  "race": "Bahrain GP",        "date": "Apr 13",  "winner": "Piastri",    "team": "McLaren",   "flag": "🇧🇭"},
        {"round": 5,  "race": "Saudi Arabian GP",  "date": "Apr 20",  "winner": "Norris",     "team": "McLaren",   "flag": "🇸🇦"},
        {"round": 6,  "race": "Miami GP",          "date": "May 4",   "winner": "Verstappen", "team": "Red Bull",  "flag": "🇺🇸"},
        {"round": 7,  "race": "Emilia Romagna GP", "date": "May 18",  "winner": "Norris",     "team": "McLaren",   "flag": "🇮🇹"},
        {"round": 8,  "race": "Monaco GP",         "date": "May 25",  "winner": "Norris",     "team": "McLaren",   "flag": "🇲🇨"},
        {"round": 9,  "race": "Spanish GP",        "date": "Jun 1",   "winner": "Piastri",    "team": "McLaren",   "flag": "🇪🇸"},
        {"round": 10, "race": "Canadian GP",       "date": "Jun 15",  "winner": "Norris",     "team": "McLaren",   "flag": "🇨🇦"},
        {"round": 11, "race": "Austrian GP",       "date": "Jun 29",  "winner": "Russell",    "team": "Mercedes",  "flag": "🇦🇹"},
        {"round": 12, "race": "British GP",        "date": "Jul 6",   "winner": "Norris",     "team": "McLaren",   "flag": "🇬🇧"},
        {"round": 13, "race": "Belgian GP",        "date": "Jul 27",  "winner": "Piastri",    "team": "McLaren",   "flag": "🇧🇪"},
        {"round": 14, "race": "Hungarian GP",      "date": "Aug 3",   "winner": "Piastri",    "team": "McLaren",   "flag": "🇭🇺"},
        {"round": 15, "race": "Dutch GP",          "date": "Aug 31",  "winner": "Norris",     "team": "McLaren",   "flag": "🇳🇱"},
        {"round": 16, "race": "Italian GP",        "date": "Sep 7",   "winner": "Leclerc",    "team": "Ferrari",   "flag": "🇮🇹"},
        {"round": 17, "race": "Azerbaijan GP",     "date": "Sep 21",  "winner": "Piastri",    "team": "McLaren",   "flag": "🇦🇿"},
        {"round": 18, "race": "Singapore GP",      "date": "Oct 5",   "winner": "Norris",     "team": "McLaren",   "flag": "🇸🇬"},
        {"round": 19, "race": "US GP",             "date": "Oct 19",  "winner": "Verstappen", "team": "Red Bull",  "flag": "🇺🇸"},
        {"round": 20, "race": "Mexico GP",         "date": "Oct 26",  "winner": "Verstappen", "team": "Red Bull",  "flag": "🇲🇽"},
        {"round": 21, "race": "São Paulo GP",      "date": "Nov 9",   "winner": "Norris",     "team": "McLaren",   "flag": "🇧🇷"},
        {"round": 22, "race": "Las Vegas GP",      "date": "Nov 22",  "winner": "Piastri",    "team": "McLaren",   "flag": "🇺🇸"},
        {"round": 23, "race": "Qatar GP",          "date": "Nov 30",  "winner": "Norris",     "team": "McLaren",   "flag": "🇶🇦"},
        {"round": 24, "race": "Abu Dhabi GP",      "date": "Dec 7",   "winner": "Verstappen", "team": "Red Bull",  "flag": "🇦🇪"},
    ]

    winner_colors = {'McLaren': '#FF8000', 'Red Bull': '#3671C6', 'Ferrari': '#DC0000', 'Mercedes': '#00D2BE'}

    for r in races_2025:
        wcolor = winner_colors.get(r['team'], '#888')
        st.markdown(f'''
        <div style="display:flex;align-items:center;gap:16px;padding:10px 16px;margin-bottom:3px;
                    background:#0f0f14;border:1px solid #1a1a28;border-left:3px solid {wcolor};
                    transition:transform 0.2s ease,box-shadow 0.2s ease,background 0.2s ease;
                    cursor:default;"
             onmouseover="this.style.transform='translateX(4px)';this.style.background='#141420';this.style.boxShadow='0 4px 18px rgba(0,0,0,0.4)'"
             onmouseout="this.style.transform='';this.style.background='#0f0f14';this.style.boxShadow=''">
            <div style="font-family:Share Tech Mono,monospace;font-size:10px;color:#2a2a3a;min-width:32px;">R{r["round"]:02d}</div>
            <div style="font-size:20px;">{r["flag"]}</div>
            <div style="flex:1;">
                <div style="font-family:Barlow Condensed,sans-serif;font-size:16px;font-weight:700;color:#fff;letter-spacing:1px;text-transform:uppercase;">{r["race"]}</div>
                <div style="font-family:Share Tech Mono,monospace;font-size:10px;color:#444;">{r["date"]} 2025</div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:Barlow Condensed,sans-serif;font-size:15px;font-weight:700;color:{wcolor};">{r["winner"]}</div>
                <div style="font-family:Share Tech Mono,monospace;font-size:10px;color:#444;">{r["team"]}</div>
            </div>
        </div>''', unsafe_allow_html=True)

    st.markdown('<div class="sec-header" style="margin-top:24px;"><div class="sec-title">2025 Championship</div><div class="sec-line"></div></div>', unsafe_allow_html=True)
    champ_data = [
        ("🥇", "Lando Norris",    "McLaren",  "NOR", "#FF8000", "1st — World Champion"),
        ("🥈", "Oscar Piastri",   "McLaren",  "PIA", "#FF8000", "2nd"),
        ("🥉", "Max Verstappen",  "Red Bull", "VER", "#3671C6", "3rd"),
    ]
    cols = st.columns(3)
    for i, (medal, name, team, code, color, pos) in enumerate(champ_data):
        cols[i].markdown(f'''
        <div style="background:#0f0f14;border:1px solid #1a1a28;border-top:2px solid {color};
                    padding:22px;text-align:center;
                    transition:transform 0.25s ease,box-shadow 0.25s ease;cursor:default;"
             onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 12px 36px rgba(0,0,0,0.5), 0 0 20px {color}22'"
             onmouseout="this.style.transform='';this.style.boxShadow=''">
            <div style="font-size:30px;margin-bottom:10px;">{medal}</div>
            <div style="font-family:Barlow Condensed,sans-serif;font-size:22px;font-weight:900;color:#fff;">{name}</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:10px;color:#444;margin-top:6px;">{team} &nbsp;·&nbsp; {pos}</div>
            <div style="width:40px;height:2px;background:{color};margin:12px auto 0;transition:width 0.3s ease;"></div>
        </div>''', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)