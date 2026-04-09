# ============================================================
# PITWALL AI — Step 2: Driver DNA + Anomaly Detection
# Run AFTER 1_collect_data.py
# Builds each driver's fingerprint and flags anomaly laps.
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import warnings, os
warnings.filterwarnings('ignore')

os.makedirs('outputs', exist_ok=True)

# ---- LOAD DATA ----
df = pd.read_csv('data/telemetry_raw.csv')
print(f"Loaded {len(df)} laps for drivers: {df['Driver'].unique()}")

# ---- DNA FEATURES — these define a driver's style ----
DNA_FEATURES = [
    'AvgSpeed', 'MaxSpeed',
    'AvgThrottle', 'ThrottleStd',
    'BrakeRatio', 'AvgRPM',
    'AvgGear', 'CoastRatio'
]

results = {}   # stores anomaly results per driver

for driver in df['Driver'].unique():
    print(f"\nBuilding DNA for {driver}...")

    d = df[df['Driver'] == driver].copy().reset_index(drop=True)
    X = d[DNA_FEATURES].dropna()
    valid_idx = X.index
    d = d.loc[valid_idx].reset_index(drop=True)
    X = X.reset_index(drop=True)

    # --- Normalize: this IS the DNA fingerprint ---
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # --- Isolation Forest: finds laps that don't match the driver's pattern ---
    # contamination=0.08 means "expect ~8% of laps to be anomalies"
    model = IsolationForest(contamination="auto", n_estimators=200, random_state=42)

# ✅ FIT MODEL (INSIDE LOOP)
    model.fit(X_scaled)

# ✅ SCORES
    scores = model.decision_function(X_scaled)

# ✅ THRESHOLD
    threshold = np.percentile(scores, 5)

# ✅ ASSIGN
    d['AnomalyScore'] = scores
    d['IsAnomaly'] = scores < threshold

# ✅ SEVERITY
    d['SeverityScore'] = model.score_samples(X_scaled)
    d['SeverityScore'] = (d['SeverityScore'] - d['SeverityScore'].min()) / \
                     (d['SeverityScore'].max() - d['SeverityScore'].min())   

    # --- Anomaly severity score (lower = more anomalous) ---
    d['SeverityScore'] = model.score_samples(X_scaled)
    d['SeverityScore'] = (d['SeverityScore'] - d['SeverityScore'].min()) / \
                         (d['SeverityScore'].max() - d['SeverityScore'].min())

    results[driver] = d
    anomalies = d[d['IsAnomaly']]
    print(f"  Total laps: {len(d)} | Anomalies flagged: {len(anomalies)}")
    print(f"  Most anomalous laps: {anomalies.sort_values('SeverityScore').head(3)[['Race','LapNumber','LapTime_s','Compound']].to_string(index=False)}")


# ============================================================
# VISUALISATION — Driver DNA Dashboard
# ============================================================

drivers  = list(results.keys())
fig      = plt.figure(figsize=(18, 12))
fig.patch.set_facecolor('#0f0f0f')
gs       = gridspec.GridSpec(3, len(drivers), figure=fig, hspace=0.45, wspace=0.3)

COLORS = {'HAM': '#00D2BE', 'VER': '#3671C6', 'LEC': '#DC0000', 'NOR': '#FF8000'}

for col, driver in enumerate(drivers):
    d     = results[driver]
    color = COLORS.get(driver, '#ffffff')
    norm  = d[~d['IsAnomaly']]
    anom  = d[d['IsAnomaly']]

    # --- Plot 1: Throttle DNA ---
    ax1 = fig.add_subplot(gs[0, col])
    ax1.set_facecolor('#1a1a1a')
    ax1.plot(norm['LapNumber'], norm['AvgThrottle'],
             color=color, linewidth=1.2, alpha=0.8, label='Normal')
    ax1.scatter(anom['LapNumber'], anom['AvgThrottle'],
                color='#ff4444', s=60, zorder=5, label='Anomaly')
    ax1.set_title(f'{driver} — Throttle DNA', color='white', fontsize=11, pad=8)
    ax1.set_ylabel('Avg throttle %', color='#aaaaaa', fontsize=9)
    ax1.tick_params(colors='#aaaaaa', labelsize=8)
    for spine in ax1.spines.values(): spine.set_color('#333333')
    ax1.legend(fontsize=8, facecolor='#1a1a1a', labelcolor='white', framealpha=0.5)

    # --- Plot 2: Speed DNA ---
    ax2 = fig.add_subplot(gs[1, col])
    ax2.set_facecolor('#1a1a1a')
    ax2.plot(norm['LapNumber'], norm['AvgSpeed'],
             color=color, linewidth=1.2, alpha=0.8)
    ax2.scatter(anom['LapNumber'], anom['AvgSpeed'],
                color='#ff4444', s=60, zorder=5)
    ax2.set_title(f'{driver} — Speed DNA', color='white', fontsize=11, pad=8)
    ax2.set_ylabel('Avg speed km/h', color='#aaaaaa', fontsize=9)
    ax2.tick_params(colors='#aaaaaa', labelsize=8)
    for spine in ax2.spines.values(): spine.set_color('#333333')

    # --- Plot 3: Anomaly severity timeline ---
    ax3 = fig.add_subplot(gs[2, col])
    ax3.set_facecolor('#1a1a1a')
    scatter = ax3.scatter(d['LapNumber'], d['SeverityScore'],
                          c=d['SeverityScore'], cmap='RdYlGn',
                          s=30, alpha=0.85, vmin=0, vmax=1)
    ax3.axhline(y=d[d['IsAnomaly']]['SeverityScore'].max() if len(anom) else 0.2,
                color='#ff4444', linestyle='--', linewidth=0.8, alpha=0.6)
    ax3.set_title(f'{driver} — Anomaly severity', color='white', fontsize=11, pad=8)
    ax3.set_ylabel('Normality score', color='#aaaaaa', fontsize=9)
    ax3.set_xlabel('Lap number', color='#aaaaaa', fontsize=9)
    ax3.tick_params(colors='#aaaaaa', labelsize=8)
    for spine in ax3.spines.values(): spine.set_color('#333333')
    cb = plt.colorbar(scatter, ax=ax3, label='0=anomaly  1=normal')
    cb.ax.yaxis.label.set_color('#aaaaaa')
    cb.ax.tick_params(colors='#aaaaaa')

fig.suptitle('PitWall AI — Driver DNA Fingerprint Dashboard',
             color='white', fontsize=16, fontweight='bold', y=0.98)

plt.savefig('outputs/driver_dna_dashboard.png', dpi=150,
            bbox_inches='tight', facecolor='#0f0f0f')
plt.show()
print("\nDashboard saved to outputs/driver_dna_dashboard.png")

# ---- Save anomaly report ----
all_anomalies = pd.concat([
    results[d][results[d]['IsAnomaly']][['Driver','Race','LapNumber','LapTime_s','Compound','SeverityScore']]
    for d in results
]).sort_values('SeverityScore')

all_anomalies.to_csv('outputs/anomaly_report.csv', index=False)
print(f"\nTop anomaly laps saved to outputs/anomaly_report.csv")
print(all_anomalies.head(10).to_string(index=False))
