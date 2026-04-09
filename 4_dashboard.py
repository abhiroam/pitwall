import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

st.set_page_config(page_title="PitWall AI", page_icon="🏎", layout="wide", initial_sidebar_state="collapsed")

query_params = st.query_params
url_driver = query_params.get('driver', None)

DRIVER_COLORS = {'HAM': '#00D2BE', 'VER': '#3671C6', 'LEC': '#DC0000', 'NOR': '#FF8000'}
DRIVER_NAMES  = {'HAM': 'Lewis Hamilton', 'VER': 'Max Verstappen', 'LEC': 'Charles Leclerc', 'NOR': 'Lando Norris'}

CHART_INFO = {
    'AvgThrottle': {'title': 'THROTTLE APPLICATION %', 'normal': 'Average throttle % across the lap. Higher = more aggressive driving style.', 'anomaly': 'ANOMALY — Throttle pattern differs from this driver\'s normal style. Could indicate tire issues or strategic backing off.', 'unit': '%'},
    'AvgSpeed':    {'title': 'AVERAGE SPEED km/h',     'normal': 'Average speed maintained across the full lap. Affected by tire condition and fuel load.', 'anomaly': 'ANOMALY — Speed outside normal range. Possible tire degradation, safety car influence, or mechanical issue.', 'unit': 'km/h'},
    'BrakeRatio':  {'title': 'BRAKE RATIO',            'normal': 'Percentage of lap spent braking. Each driver has a unique braking fingerprint.', 'anomaly': 'ANOMALY — Braking behaviour changed from baseline. Could signal tire wear or car handling issue.', 'unit': ''}
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@300;400;500;600&family=Share+Tech+Mono&display=swap');
html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }

.stApp { background-color: #15151e; }
section[data-testid="stSidebar"] { display:none !important; }
header[data-testid="stHeader"] { display:none !important; }
.block-container { padding:0 !important; max-width:100% !important; }

.top-nav {
    position:sticky; top:0; z-index:999;
    background:#1a1a27;
    border-bottom:1px solid #38383f;
    display:flex; align-items:center; justify-content:space-between;
    padding:0 40px; height:60px;
}
.nav-logo { font-family:'Barlow Condensed',sans-serif; font-size:26px; font-weight:900; letter-spacing:2px; text-transform:uppercase; color:#fff; }
.nav-logo span { color:#e8001d; }
.nav-home { font-family:'Barlow Condensed',sans-serif; font-size:14px; font-weight:700; color:#959595; letter-spacing:2px; text-decoration:none; text-transform:uppercase; transition:color 0.2s; }
.nav-home:hover { color:#ffffff; }
.redbar { height:3px; background:#e8001d; width:100%; }
.dash-content { padding:12px 40px; }

.metric-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:2px; margin-bottom:16px; }
.metric-card { background:#1f1f2e; border:1px solid #38383f; border-top:3px solid #e8001d; padding:16px 20px; }
.metric-label { font-family:'Barlow Condensed',sans-serif; font-size:15px; font-weight:700; color:#ffffff; letter-spacing:3px; text-transform:uppercase; margin-bottom:8px; }
.metric-value { font-family:'Barlow Condensed',sans-serif; font-size:52px; font-weight:900; color:#ffffff; line-height:1; }
.metric-value.red { color:#e8001d; }
.metric-sub { font-family:'Barlow Condensed',sans-serif; font-size:13px; color:#959595; margin-top:4px; letter-spacing:1px; }

.sec-header { display:flex; align-items:center; gap:12px; margin:16px 0 12px; padding-bottom:8px; border-bottom:1px solid #38383f; }
.sec-title { font-family:'Barlow Condensed',sans-serif; font-size:24px; font-weight:900; color:#ffffff; letter-spacing:3px; text-transform:uppercase; }
.sec-line { flex:1; height:1px; background:linear-gradient(to right,#38383f,transparent); }
.sec-tag { font-family:'Barlow Condensed',sans-serif; font-size:11px; font-weight:700; color:#959595; letter-spacing:2px; border:1px solid #38383f; padding:3px 10px; text-transform:uppercase; }

.alert-card { background:#1f1f2e; border:1px solid #38383f; border-left:3px solid #e8001d; padding:16px 20px; margin-bottom:6px; display:flex; align-items:center; gap:16px; }
.alert-lap { font-family:'Barlow Condensed',sans-serif; font-size:36px; font-weight:900; color:#ffffff; min-width:70px; line-height:1; }
.alert-lap span { font-size:11px; color:#959595; display:block; font-family:'Barlow Condensed',sans-serif; font-weight:700; letter-spacing:2px; text-transform:uppercase; }
.alert-info { flex:1; }
.alert-driver { font-family:'Barlow Condensed',sans-serif; font-size:18px; font-weight:700; color:#ffffff; letter-spacing:1px; text-transform:uppercase; }
.alert-detail { font-family:'Barlow',sans-serif; font-size:13px; color:#959595; margin-top:4px; }
.sev-wrap { min-width:140px; }
.sev-label { font-family:'Barlow Condensed',sans-serif; font-size:13px; font-weight:700; color:#ffffff; text-align:right; margin-bottom:6px; letter-spacing:1px; }
.sev-bar { height:3px; background:#38383f; border-radius:2px; overflow:hidden; }
.sev-fill { height:100%; background:#e8001d; }

.radio-card { background:#1f1f2e; border:1px solid #38383f; border-left:3px solid #00d2be; padding:18px 22px; margin-bottom:10px; }
.radio-header { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.radio-dot { width:8px; height:8px; background:#00d2be; border-radius:50%; }
.radio-time { font-family:'Barlow Condensed',sans-serif; font-size:13px; font-weight:700; color:#959595; letter-spacing:2px; text-transform:uppercase; }
.radio-meta { font-family:'Barlow Condensed',sans-serif; font-size:13px; font-weight:700; color:#959595; letter-spacing:2px; text-transform:uppercase; }
.radio-tag { margin-left:auto; font-family:'Barlow Condensed',sans-serif; font-size:13px; font-weight:700; padding:3px 10px; border-radius:2px; }
.radio-msg { font-family:'Barlow',sans-serif; font-size:16px; color:#ffffff; line-height:1.8; padding:14px 18px; background:#15151e; border:1px solid #38383f; border-radius:2px; }

.badge-HAM { background:rgba(0,210,190,0.15); color:#00d2be; border:1px solid #00d2be; padding:3px 10px; border-radius:2px; font-family:'Barlow Condensed',sans-serif; font-size:14px; font-weight:700; }
.badge-VER { background:rgba(54,113,198,0.15); color:#3671c6; border:1px solid #3671c6; padding:3px 10px; border-radius:2px; font-family:'Barlow Condensed',sans-serif; font-size:14px; font-weight:700; }
.badge-LEC { background:rgba(220,0,0,0.15); color:#e8001d; border:1px solid #e8001d; padding:3px 10px; border-radius:2px; font-family:'Barlow Condensed',sans-serif; font-size:14px; font-weight:700; }
.badge-NOR { background:rgba(255,128,0,0.15); color:#ff8000; border:1px solid #ff8000; padding:3px 10px; border-radius:2px; font-family:'Barlow Condensed',sans-serif; font-size:14px; font-weight:700; }

.fastest-card { background:#1a2a1a; border:1px solid #38383f; border-left:3px solid #00ff88; padding:18px 22px; margin-bottom:10px; }
.fastest-label { font-family:'Barlow Condensed',sans-serif; font-size:13px; font-weight:700; color:#00ff88; letter-spacing:3px; text-transform:uppercase; margin-bottom:6px; }
.fastest-time { font-family:'Barlow Condensed',sans-serif; font-size:44px; font-weight:900; color:#fff; line-height:1; }

/* Page buttons — F1 style nav tabs */
div.stButton > button {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 14px !important; font-weight: 700 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    background: #1a1a27 !important; color: #959595 !important;
    border: none !important; border-bottom: 3px solid transparent !important;
    border-radius: 0 !important; padding: 12px 4px !important;
    transition: all 0.2s !important;
}
div.stButton > button:hover { color: #fff !important; border-bottom: 3px solid #38383f !important; }
div.stButton > button:focus { color: #fff !important; border-bottom: 3px solid #e8001d !important; box-shadow: none !important; }

.stSelectbox label { font-family:'Barlow Condensed',sans-serif !important; font-size:16px !important; font-weight:700 !important; color:#ffffff !important; letter-spacing:3px !important; text-transform:uppercase !important; }
.stSelectbox > div > div { background:#1f1f2e !important; border:1px solid #38383f !important; color:#ffffff !important; border-radius:2px !important; font-family:'Barlow Condensed',sans-serif !important; font-size:16px !important; font-weight:700 !important; }

.stTabs [data-baseweb="tab-list"] { background:#1a1a27 !important; border-bottom:1px solid #38383f !important; gap:0 !important; padding:0 !important; }
.stTabs [data-baseweb="tab"] { font-family:'Barlow Condensed',sans-serif !important; font-size:14px !important; font-weight:700 !important; letter-spacing:2px !important; text-transform:uppercase !important; color:#959595 !important; background:transparent !important; border:none !important; padding:14px 20px !important; white-space:nowrap !important; }
.stTabs [aria-selected="true"] { color:#ffffff !important; border-bottom:3px solid #e8001d !important; }
.stTabs [data-baseweb="tab"]:hover { color:#ffffff !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    tel  = pd.read_csv('data/telemetry_raw.csv')     if os.path.exists('data/telemetry_raw.csv')     else pd.DataFrame()
    anom = pd.read_csv('outputs/anomaly_report.csv') if os.path.exists('outputs/anomaly_report.csv') else pd.DataFrame()
    rad  = pd.read_csv('outputs/radio_messages.csv') if os.path.exists('outputs/radio_messages.csv') else pd.DataFrame()
    return tel, anom, rad

tel_df, anom_df, radio_df = load_data()

# ---- NAV ----
if 'page' not in st.session_state:
    st.session_state.page = 'DNA FINGERPRINT'

pages = ['DNA FINGERPRINT', 'VS COMPARISON', 'ANOMALY TIMELINE', 'FASTEST LAP', 'AI RADIO FEED', 'EXPORT REPORT', 'F1 NEWS']

st.markdown("""
<div class="redbar"></div>
<div class="top-nav">
    <div class="nav-logo">Pit<span>Wall</span> AI</div>
    <div><a class="nav-home" href="javascript:history.back()">Back to Site</a></div>
</div>
""", unsafe_allow_html=True)

# Page selector buttons styled like tabs
cols = st.columns(len(pages))
for i, page in enumerate(pages):
    with cols[i]:
        if st.button(page, key=f'btn_{i}', use_container_width=True):
            st.session_state.page = page

current_page = st.session_state.page

st.markdown('<div class="dash-content">', unsafe_allow_html=True)

# ---- SELECTORS ----
drivers_avail = tel_df['Driver'].unique().tolist() if not tel_df.empty else ['HAM','VER']
races_avail   = tel_df['Race'].unique().tolist()   if not tel_df.empty else []
default_idx   = drivers_avail.index(url_driver) if url_driver and url_driver in drivers_avail else 0

sel_col1, sel_col2, sel_col3, sel_col4 = st.columns([2, 2, 2, 4])
with sel_col1:
    sel_driver = st.selectbox("DRIVER", drivers_avail, index=default_idx)
with sel_col2:
    sel_race = st.selectbox("RACE", races_avail) if races_avail else None
with sel_col3:
    compare_drivers = [d for d in drivers_avail if d != sel_driver]
    compare_driver  = st.selectbox("COMPARE WITH", ['None'] + compare_drivers)

dcolor  = DRIVER_COLORS.get(sel_driver, '#E8001D')
dname   = DRIVER_NAMES.get(sel_driver, sel_driver)

# ---- METRICS ----
if not anom_df.empty:
    d_anom = anom_df[anom_df['Driver']==sel_driver]
    d_tel  = tel_df[tel_df['Driver']==sel_driver]
    total  = len(d_tel)
    anoms  = len(d_anom)
    pct    = round(anoms/total*100,1) if total else 0
    spd    = round(d_tel['AvgSpeed'].mean(),1) if not d_tel.empty else 0
    thr    = round(d_tel['AvgThrottle'].mean(),1) if not d_tel.empty else 0
    st.markdown(f"""
    <div style="margin:8px 0 6px;font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:700;color:#ffffff;letter-spacing:3px;">{sel_driver} &nbsp;<span style='color:#555'>·</span>&nbsp; {dname} &nbsp;<span style='color:#555'>·</span>&nbsp; 2024 SEASON</div>
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-label">Laps Analyzed</div><div class="metric-value">{total}</div><div class="metric-sub">Across 3 Grand Prix</div></div>
        <div class="metric-card"><div class="metric-label">Anomalies Detected</div><div class="metric-value red">{anoms}</div><div class="metric-sub">{pct}% of laps flagged</div></div>
        <div class="metric-card"><div class="metric-label">Avg Speed</div><div class="metric-value">{spd}</div><div class="metric-sub">km/h across dataset</div></div>
        <div class="metric-card"><div class="metric-label">Avg Throttle</div><div class="metric-value">{thr}<span style="font-size:18px;color:#555">%</span></div><div class="metric-sub">Aggression index</div></div>
    </div>""", unsafe_allow_html=True)

# ---- TABS ----
# Page based rendering

# ==============================
# TAB 1 — DNA FINGERPRINT
# ==============================
if current_page == "DNA FINGERPRINT":
    st.markdown('<div class="sec-header"><div class="sec-title">Telemetry DNA</div><div class="sec-line"></div><div class="sec-tag">HOVER FOR INSIGHTS</div></div>', unsafe_allow_html=True)
    if not tel_df.empty and sel_race:
        race_data = tel_df[(tel_df['Driver']==sel_driver) & (tel_df['Race']==sel_race)].copy()
        if not anom_df.empty:
            a_laps = set(anom_df[(anom_df['Driver']==sel_driver) & (anom_df['Race']==sel_race)]['LapNumber'].tolist())
            race_data['IsAnomaly'] = race_data['LapNumber'].isin(a_laps)
        else:
            race_data['IsAnomaly'] = False
        if not race_data.empty:
            norm = race_data[~race_data['IsAnomaly']]
            anom = race_data[race_data['IsAnomaly']]
            for col, info in CHART_INFO.items():
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=norm['LapNumber'], y=norm[col], mode='lines+markers', name=f'{sel_driver} baseline',
                    line=dict(color=dcolor, width=2.5), marker=dict(size=5, color=dcolor),
                    fill='tozeroy', fillcolor=f'rgba({int(dcolor[1:3],16)},{int(dcolor[3:5],16)},{int(dcolor[5:7],16)},0.06)',
                    hovertemplate=f'<b>LAP %{{x}}</b><br>{info["title"]}: <b>%{{y:.2f}}{info["unit"]}</b><br><span style="color:#aaa;font-size:11px">{info["normal"]}</span><extra></extra>'))
                if not anom.empty:
                    fig.add_trace(go.Scatter(x=anom['LapNumber'], y=anom[col], mode='markers', name='Anomaly',
                        marker=dict(size=14, color='#E8001D', symbol='triangle-down', line=dict(color='#ff8888', width=1.5)),
                        hovertemplate=f'<b>⚠ ANOMALY — LAP %{{x}}</b><br>{info["title"]}: <b>%{{y:.2f}}{info["unit"]}</b><br><span style="color:#ff6666;font-size:11px">{info["anomaly"]}</span><extra></extra>'))
                fig.update_layout(title=dict(text=f'{info["title"]}  <span style="font-size:11px;color:#444">— {sel_driver} · {sel_race} 2024</span>', font=dict(size=13,color='#ffffff',family='monospace'),x=0),
                    plot_bgcolor='#0f0f0f', paper_bgcolor='#080808', font=dict(color='#cccccc',family='monospace'), height=260,
                    margin=dict(l=60,r=20,t=44,b=36), legend=dict(bgcolor='#111',bordercolor='#222',borderwidth=1,font=dict(color='#ccc',size=10)),
                    xaxis=dict(title='Lap Number',gridcolor='#2e2e40',color='#cccccc',showline=True,linecolor='#2e2e40'),
                    yaxis=dict(gridcolor='#2e2e40',color='#cccccc',showline=True,linecolor='#2e2e40'),
                    hoverlabel=dict(bgcolor='#111',bordercolor='#333',font=dict(color='#fff',size=12,family='monospace')), hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==============================
# TAB 2 — VS COMPARISON
# ==============================
if current_page == "VS COMPARISON":
    st.markdown('<div class="sec-header"><div class="sec-title">Driver vs Driver</div><div class="sec-line"></div><div class="sec-tag">HEAD TO HEAD</div></div>', unsafe_allow_html=True)
    if compare_driver != 'None' and sel_race and not tel_df.empty:
        d1 = tel_df[(tel_df['Driver']==sel_driver) & (tel_df['Race']==sel_race)]
        d2 = tel_df[(tel_df['Driver']==compare_driver) & (tel_df['Race']==sel_race)]
        c2color = DRIVER_COLORS.get(compare_driver, '#888888')
        for col, info in CHART_INFO.items():
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=d1['LapNumber'], y=d1[col], mode='lines+markers', name=sel_driver,
                line=dict(color=dcolor, width=2.5), marker=dict(size=5),
                hovertemplate=f'<b>{sel_driver} LAP %{{x}}</b><br>{info["title"]}: <b>%{{y:.2f}}{info["unit"]}</b><extra></extra>'))
            fig.add_trace(go.Scatter(x=d2['LapNumber'], y=d2[col], mode='lines+markers', name=compare_driver,
                line=dict(color=c2color, width=2.5, dash='dot'), marker=dict(size=5),
                hovertemplate=f'<b>{compare_driver} LAP %{{x}}</b><br>{info["title"]}: <b>%{{y:.2f}}{info["unit"]}</b><extra></extra>'))
            fig.update_layout(title=dict(text=f'{info["title"]}  <span style="font-size:11px;color:#444">— {sel_driver} vs {compare_driver} · {sel_race}</span>', font=dict(size=13,color='#ffffff',family='monospace'),x=0),
                plot_bgcolor='#0f0f0f', paper_bgcolor='#080808', font=dict(color='#cccccc',family='monospace'), height=260,
                margin=dict(l=60,r=20,t=44,b=36), legend=dict(bgcolor='#111',bordercolor='#222',borderwidth=1,font=dict(color='#ccc',size=10)),
                xaxis=dict(title='Lap Number',gridcolor='#2e2e40',color='#cccccc'), yaxis=dict(gridcolor='#2e2e40',color='#cccccc'),
                hoverlabel=dict(bgcolor='#111',bordercolor='#333',font=dict(color='#fff',size=12,family='monospace')), hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # Quick stat comparison
        st.markdown('<div class="sec-header"><div class="sec-title">Head to Head Stats</div><div class="sec-line"></div></div>', unsafe_allow_html=True)
        stat_cols = st.columns(3)
        metrics = [('AvgSpeed','Avg Speed','km/h'), ('AvgThrottle','Avg Throttle','%'), ('BrakeRatio','Brake Ratio','')]
        for i, (metric_col, label, unit) in enumerate(metrics):
            v1 = round(d1[metric_col].mean(), 2) if not d1.empty else 0
            v2 = round(d2[metric_col].mean(), 2) if not d2.empty else 0

            stat_cols[i].metric(f"{label}", f"{v1}{unit}", f"{round(v1-v2,2)}{unit} vs {compare_driver}")
    else:
        st.info("Select a driver to compare with using the COMPARE WITH dropdown above.")

# ==============================
# TAB 3 — ANOMALY TIMELINE
# ==============================
if current_page == "ANOMALY TIMELINE":
    st.markdown('<div class="sec-header"><div class="sec-title">Anomaly Timeline</div><div class="sec-line"></div><div class="sec-tag">RACE HEARTBEAT</div></div>', unsafe_allow_html=True)
    if not anom_df.empty and not tel_df.empty and sel_race:
        race_data = tel_df[(tel_df['Driver']==sel_driver) & (tel_df['Race']==sel_race)].copy()
        race_anom = anom_df[(anom_df['Driver']==sel_driver) & (anom_df['Race']==sel_race)].copy()
        if not race_data.empty:
            race_data['Severity'] = 0.0
            for _, row in race_anom.iterrows():
                sev = round((1 - row['SeverityScore']) * 100, 1)
                race_data.loc[race_data['LapNumber']==row['LapNumber'], 'Severity'] = sev

            fig = go.Figure()
            # Background bars for all laps
            fig.add_trace(go.Bar(x=race_data['LapNumber'], y=[100]*len(race_data),
                marker_color='#111111', name='Normal lap',
                hovertemplate='LAP %{x} — Normal<extra></extra>'))
            # Anomaly bars
            anom_data = race_data[race_data['Severity'] > 0]
            fig.add_trace(go.Bar(x=anom_data['LapNumber'], y=anom_data['Severity'],
                marker=dict(color=anom_data['Severity'], colorscale=[[0,'#ff8800'],[1,'#E8001D']], showscale=True,
                    colorbar=dict(title=dict(text='Severity %', font=dict(color='#888')), tickfont=dict(color='#888'))),
                name='Anomaly severity',
                hovertemplate='<b>⚠ LAP %{x}</b><br>Severity: <b>%{y:.1f}%</b> off baseline<extra></extra>'))
            fig.update_layout(
                title=dict(text=f'Race Anomaly Timeline — {sel_driver} · {sel_race} 2024  <span style="font-size:11px;color:#555">| Red = most anomalous laps</span>', font=dict(size=13,color='#ffffff',family='monospace'),x=0),
                plot_bgcolor='#0f0f0f', paper_bgcolor='#080808', barmode='overlay',
                font=dict(color='#cccccc',family='monospace'), height=320,
                margin=dict(l=60,r=60,t=50,b=40),
                xaxis=dict(title='Lap Number',gridcolor='#2e2e40',color='#cccccc'),
                yaxis=dict(title='Anomaly Severity %',gridcolor='#2e2e40',color='#cccccc',range=[0,105]),
                hoverlabel=dict(bgcolor='#111',bordercolor='#333',font=dict(color='#fff',size=12,family='monospace')),
                legend=dict(bgcolor='#111',bordercolor='#222',font=dict(color='#ccc',size=10)))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            # Summary
            if not race_anom.empty:
                worst = race_anom.sort_values('SeverityScore').iloc[0]
                worst_sev = round((1 - worst['SeverityScore']) * 100, 1)
                st.markdown(f"""
                <div class="alert-card" style="margin-top:16px;">
                    <div class="alert-lap">{int(worst['LapNumber'])}<span>WORST LAP</span></div>
                    <div class="alert-info">
                        <div class="alert-driver"><span class="badge-{sel_driver}">{sel_driver}</span>&nbsp; Most anomalous lap in {sel_race}</div>
                        <div class="alert-detail">TIRE: {worst['Compound']} &nbsp;·&nbsp; {worst_sev}% deviation from driver baseline &nbsp;·&nbsp; LAP TIME: {round(worst['LapTime_s'],2)}s</div>
                    </div>
                </div>""", unsafe_allow_html=True)

# ==============================
# TAB 4 — FASTEST LAP
# ==============================
if current_page == "FASTEST LAP":
    st.markdown('<div class="sec-header"><div class="sec-title">Fastest Lap Analysis</div><div class="sec-line"></div><div class="sec-tag">PEAK PERFORMANCE</div></div>', unsafe_allow_html=True)
    if not tel_df.empty and sel_race:
        race_data = tel_df[(tel_df['Driver']==sel_driver) & (tel_df['Race']==sel_race)].copy().dropna(subset=['LapTime_s'])
        if not race_data.empty:
            fastest = race_data.loc[race_data['LapTime_s'].idxmin()]
            slowest = race_data.loc[race_data['LapTime_s'].idxmax()]
            avg_time = race_data['LapTime_s'].mean()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="fastest-card">
                    <div class="fastest-label">Fastest Lap</div>
                    <div class="fastest-time">{int(fastest['LapTime_s']//60)}:{fastest['LapTime_s']%60:06.3f}</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#888;margin-top:6px;">LAP {int(fastest['LapNumber'])} &nbsp;·&nbsp; {fastest['Compound']}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Average Lap Time</div>
                    <div class="metric-value" style="font-size:28px;">{int(avg_time//60)}:{avg_time%60:06.3f}</div>
                    <div class="metric-sub">Across {len(race_data)} laps</div>
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
                a_laps = set(anom_df[(anom_df['Driver']==sel_driver)&(anom_df['Race']==sel_race)]['LapNumber'].tolist())
                race_data['IsAnomaly'] = race_data['LapNumber'].isin(a_laps)
            else:
                race_data['IsAnomaly'] = False

            norm = race_data[~race_data['IsAnomaly']]
            anom = race_data[race_data['IsAnomaly']]

            fig.add_trace(go.Scatter(x=norm['LapNumber'], y=norm['LapTime_s'], mode='lines+markers', name='Lap time',
                line=dict(color=dcolor, width=2), marker=dict(size=5),
                hovertemplate='LAP %{x}<br>Time: <b>%{y:.3f}s</b><extra></extra>'))
            if not anom.empty:
                fig.add_trace(go.Scatter(x=anom['LapNumber'], y=anom['LapTime_s'], mode='markers', name='Anomaly lap',
                    marker=dict(size=12, color='#E8001D', symbol='triangle-down'),
                    hovertemplate='⚠ ANOMALY LAP %{x}<br>Time: <b>%{y:.3f}s</b><extra></extra>'))
            # Mark fastest lap
            fig.add_vline(x=fastest['LapNumber'], line_color='#00ff88', line_dash='dash', line_width=1,
                annotation_text=f"Fastest", annotation_font_color='#00ff88', annotation_font_size=10)

            fig.update_layout(title=dict(text=f'LAP TIMES — {sel_driver} · {sel_race} 2024', font=dict(size=13,color='#ffffff',family='monospace'),x=0),
                plot_bgcolor='#0f0f0f', paper_bgcolor='#080808', font=dict(color='#cccccc',family='monospace'), height=280,
                margin=dict(l=60,r=20,t=44,b=36), legend=dict(bgcolor='#111',bordercolor='#222',font=dict(color='#ccc',size=10)),
                xaxis=dict(title='Lap Number',gridcolor='#2e2e40',color='#cccccc'),
                yaxis=dict(title='Lap Time (s)',gridcolor='#2e2e40',color='#cccccc'),
                hoverlabel=dict(bgcolor='#111',bordercolor='#333',font=dict(color='#fff',size=12,family='monospace')))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==============================
# TAB 5 — AI RADIO FEED
# ==============================
if current_page == "AI RADIO FEED":
    st.markdown('<div class="sec-header"><div class="sec-title">Team Radio Feed</div><div class="sec-line"></div><div class="sec-tag">GROQ / LLAMA 3.3</div></div>', unsafe_allow_html=True)
    if not radio_df.empty:
        driver_radio = radio_df[radio_df['Driver']==sel_driver].sort_values('LapNumber')
        if not driver_radio.empty:
            st.markdown(f"""
            <div style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#555;letter-spacing:3px;margin-bottom:20px;">
                {len(driver_radio)} MESSAGES &nbsp;·&nbsp; {sel_driver} &nbsp;·&nbsp; 2024 SEASON &nbsp;·&nbsp; AI GENERATED
            </div>""", unsafe_allow_html=True)
            for _, row in driver_radio.iterrows():
                sev = row['Severity']
                urgency = "CRITICAL" if sev > 80 else "WARNING" if sev > 50 else "INFO"
                urgency_color = "#E8001D" if sev > 80 else "#ff8800" if sev > 50 else "#00D2BE"
                st.markdown(f"""
                <div class="radio-card">
                    <div class="radio-header">
                        <div class="radio-dot" style="background:{urgency_color}"></div>
                        <div class="radio-time">{urgency} &nbsp;·&nbsp; LAP {int(row['LapNumber'])} &nbsp;·&nbsp; {row['Race'].upper()} &nbsp;·&nbsp; {row['Compound']} TIRES</div>
                        <div class="radio-tag badge-{sel_driver}">{sel_driver}</div>
                    </div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:9px;color:#333;margin-bottom:8px;letter-spacing:2px;">
                        ENGINEER TO DRIVER &nbsp;·&nbsp; {sev}% DEVIATION FROM BASELINE
                    </div>
                    <div class="radio-msg">{str(row['RadioMsg'])}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No radio messages for this driver.")
    else:
        st.info("Run 3_ai_copilot.py first.")

# ==============================
# TAB 6 — EXPORT PDF
# ==============================
if current_page == "EXPORT REPORT":
    st.markdown('<div class="sec-header"><div class="sec-title">Export Report</div><div class="sec-line"></div><div class="sec-tag">PDF</div></div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-family:'Barlow',sans-serif;font-size:15px;color:#aaa;margin-bottom:24px;line-height:1.8;">
        Generate a complete anomaly report for <strong style="color:#fff">{dname} ({sel_driver})</strong> 
        including all flagged laps, severity scores, tire data and AI radio messages.
    </div>""", unsafe_allow_html=True)

    if st.button("GENERATE PDF REPORT", type="primary"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=24, textColor=colors.HexColor('#E8001D'), spaceAfter=6)
        sub_style   = ParagraphStyle('sub',   fontName='Helvetica',      fontSize=10, textColor=colors.HexColor('#888888'), spaceAfter=16)
        h2_style    = ParagraphStyle('h2',    fontName='Helvetica-Bold', fontSize=14, textColor=colors.black, spaceAfter=8, spaceBefore=16)
        body_style  = ParagraphStyle('body',  fontName='Helvetica',      fontSize=10, textColor=colors.HexColor('#333333'), spaceAfter=6, leading=14)

        story.append(Paragraph("PITWALL AI", title_style))
        story.append(Paragraph(f"Anomaly Report — {dname} ({sel_driver}) — 2024 Season", sub_style))
        story.append(Spacer(1, 8*mm))

        # Summary
        if not anom_df.empty:
            d_anom = anom_df[anom_df['Driver']==sel_driver]
            d_tel  = tel_df[tel_df['Driver']==sel_driver]
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
                ('BACKGROUND',(0,0),(-1,0), colors.HexColor('#E8001D')),
                ('TEXTCOLOR',(0,0),(-1,0), colors.white),
                ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                ('FONTSIZE',(0,0),(-1,-1),10),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f9f9f9'), colors.white]),
                ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#dddddd')),
                ('TOPPADDING',(0,0),(-1,-1),6), ('BOTTOMPADDING',(0,0),(-1,-1),6),
                ('LEFTPADDING',(0,0),(-1,-1),8),
            ]))
            story.append(t)
            story.append(Spacer(1, 6*mm))

            # Anomaly table
            story.append(Paragraph("Anomaly Lap Details", h2_style))
            anom_sorted = d_anom.sort_values('SeverityScore')
            table_data = [['Race', 'Lap', 'Tire', 'Lap Time', 'Severity']]
            for _, row in anom_sorted.iterrows():
                sev = round((1 - row['SeverityScore']) * 100, 1)
                table_data.append([row['Race'], str(int(row['LapNumber'])), row['Compound'], f"{round(row['LapTime_s'],2)}s", f"{sev}%"])
            t2 = Table(table_data, colWidths=[40*mm, 20*mm, 25*mm, 35*mm, 30*mm])
            t2.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0), colors.HexColor('#111111')),
                ('TEXTCOLOR',(0,0),(-1,0), colors.white),
                ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                ('FONTSIZE',(0,0),(-1,-1),9),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f9f9f9'), colors.white]),
                ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#dddddd')),
                ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
                ('LEFTPADDING',(0,0),(-1,-1),6),
            ]))
            story.append(t2)
            story.append(Spacer(1, 6*mm))

        # Radio messages
        if not radio_df.empty:
            driver_radio = radio_df[radio_df['Driver']==sel_driver]
            if not driver_radio.empty:
                story.append(Paragraph("AI Race Engineer Radio Messages", h2_style))
                for _, row in driver_radio.iterrows():
                    story.append(Paragraph(f"Lap {int(row['LapNumber'])} — {row['Race']} — {row['Compound']} tires — {row['Severity']}% anomaly", ParagraphStyle('lbl', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#E8001D'), spaceAfter=2)))
                    story.append(Paragraph(str(row['RadioMsg']), body_style))
                    story.append(Spacer(1, 3*mm))

        story.append(Spacer(1, 8*mm))
        story.append(Paragraph("Generated by PitWall AI — Code 1 Hackathon 2026 — FastF1 · scikit-learn · Groq", ParagraphStyle('footer', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#aaaaaa'))))

        doc.build(story)
        buffer.seek(0)
        st.download_button(
            label=f"DOWNLOAD {sel_driver} REPORT PDF",
            data=buffer,
            file_name=f"pitwall_ai_{sel_driver}_report.pdf",
            mime="application/pdf"
        )

# ==============================
# TAB 7 — F1 NEWS & SCHEDULE
# ==============================
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
        <div style="display:flex;align-items:center;gap:16px;padding:10px 16px;margin-bottom:4px;background:#0f0f0f;border:1px solid #1a1a1a;border-left:3px solid {wcolor};">
            <div style="font-family:Share Tech Mono,monospace;font-size:11px;color:#333;min-width:32px;">R{r["round"]:02d}</div>
            <div style="font-size:20px;">{r["flag"]}</div>
            <div style="flex:1;">
                <div style="font-family:Barlow Condensed,sans-serif;font-size:16px;font-weight:700;color:#fff;letter-spacing:1px;text-transform:uppercase;">{r["race"]}</div>
                <div style="font-family:Share Tech Mono,monospace;font-size:10px;color:#555;">{r["date"]} 2025</div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:Barlow Condensed,sans-serif;font-size:15px;font-weight:700;color:{wcolor};">{r["winner"]}</div>
                <div style="font-family:Share Tech Mono,monospace;font-size:10px;color:#555;">{r["team"]}</div>
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
        <div style="background:#111;border:1px solid #1a1a1a;border-top:2px solid {color};padding:20px;text-align:center;">
            <div style="font-size:28px;margin-bottom:8px;">{medal}</div>
            <div style="font-family:Barlow Condensed,sans-serif;font-size:22px;font-weight:900;color:#fff;">{name}</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:10px;color:#555;margin-top:4px;">{team} &nbsp;·&nbsp; {pos}</div>
        </div>''', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)