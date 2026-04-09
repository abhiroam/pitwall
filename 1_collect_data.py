# ============================================================
# PITWALL AI — Step 1: Data Collection
# Run this first. It downloads real F1 telemetry via FastF1.
# Takes ~10-20 mins first run (cached after that, instant).
# ============================================================


import pandas as pd
import os
import fastf1

# ✅ ADD THIS
fastf1.Cache.enable_cache('f1_cache')
fastf1.Cache.set_size_limit(2 * 1024**3)  # 2GB limit

# Create cache folder so data saves locally
os.makedirs('f1_cache', exist_ok=True)
os.makedirs('data', exist_ok=True)


# ---- CONFIG — change drivers/races here if you want ----
DRIVERS = ['HAM', 'VER', 'LEC', 'NOR']      # Hamilton vs Verstappen
RACES    = ['Bahrain', 'Jeddah', 'Melbourne']  # 3 rounds of 2024
YEAR     = 2024
SESSION  = 'R'                     # R = Race, Q = Qualifying
# --------------------------------------------------------

all_records = []

for race in RACES:
    print(f"\nLoading {YEAR} {race}...")
    try:
        session = fastf1.get_session(YEAR, race, SESSION)
        session.load(telemetry=True, weather=False, messages=False)

        for driver in DRIVERS:
            print(f"  Extracting {driver}...")
            laps = session.laps.pick_drivers(driver).reset_index(drop=True)

            for _, lap in laps.iterrows():
                try:
                    tel = lap.get_telemetry()
                    if tel is None or len(tel) < 50:
                        continue

                    all_records.append({
                        'Race'        : race,
                        'Driver'      : driver,
                        'LapNumber'   : int(lap['LapNumber']),
                        'LapTime_s'   : lap['LapTime'].total_seconds() if pd.notna(lap['LapTime']) else None,
                        'Compound'    : lap['Compound'],
                        'TyreLife'    : lap['TyreLife'],
                        # --- DNA FEATURES ---
                        'AvgSpeed'    : round(tel['Speed'].mean(), 2),
                        'MaxSpeed'    : round(tel['Speed'].max(), 2),
                        'AvgThrottle' : round(tel['Throttle'].mean(), 2),
                        'ThrottleStd' : round(tel['Throttle'].std(), 2),
                        'BrakeRatio'  : round(tel['Brake'].mean(), 4),   # % of lap braking
                        'AvgRPM'      : round(tel['RPM'].mean(), 2),
                        'MaxRPM'      : round(tel['RPM'].max(), 2),
                        'AvgGear'     : round(tel['nGear'].mean(), 2),
                        'CoastRatio'  : round(((tel['Throttle'] < 5) & (~tel['Brake'])).mean(), 4),
                    })
                except Exception as e:
                    pass  # skip laps with missing telemetry silently

    except Exception as e:
        print(f"  Could not load {race}: {e}")

# Save to CSV
df = pd.DataFrame(all_records).dropna(subset=['LapTime_s'])
df.to_csv('data/telemetry_raw.csv', index=False)

print(f"\nDone! Saved {len(df)} laps to data/telemetry_raw.csv")
print(df.groupby(['Driver', 'Race'])['LapNumber'].count().to_string())
