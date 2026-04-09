# ============================================================
# PITWALL AI — README
# ============================================================

## Setup

1. Install dependencies:
   pip install fastf1 pandas matplotlib scikit-learn streamlit requests

2. Run in order:
   python 1_collect_data.py       # ~15 mins first run (cached after)
   python 2_dna_model.py          # ~2 mins
   python 3_ai_copilot.py         # needs API key (see below)
   streamlit run 4_dashboard.py   # opens browser automatically

## Getting your Claude API key (free)
1. Go to https://console.anthropic.com
2. Sign up / log in
3. Click "API Keys" → "Create Key"
4. Paste it into 3_ai_copilot.py where it says YOUR_API_KEY_HERE

## Folder structure after running:
pitwall_ai/
├── 1_collect_data.py
├── 2_dna_model.py
├── 3_ai_copilot.py
├── 4_dashboard.py
├── f1_cache/          ← auto-created, stores downloaded F1 data
├── data/
│   └── telemetry_raw.csv
└── outputs/
    ├── driver_dna_dashboard.png
    ├── anomaly_report.csv
    └── radio_messages.csv

## Changing drivers or races
Edit the CONFIG section at the top of 1_collect_data.py:
   DRIVERS = ['HAM', 'VER']
   RACES   = ['Bahrain', 'Jeddah', 'Melbourne']
   YEAR    = 2024

Available driver codes: HAM, VER, LEC, NOR, SAI, RUS, PIA, ALO, etc.
Available races: any 2024 GP name e.g. 'Monaco', 'Silverstone', 'Monza'
