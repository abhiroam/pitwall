import pandas as pd
import time
import os
import requests
from dotenv import load_dotenv


# Load environment variables
from pathlib import Path

print("RUNNING FILE:", __file__)
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
# Get API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Safety check
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found. Please set it in your .env file.")

os.makedirs('outputs', exist_ok=True)



def generate_radio_message(anomaly_row: dict, retries: int = 3) -> str:
    prompt = f"""You are an F1 race engineer speaking to your driver over team radio.
Keep it to 1-2 sentences max. Sound calm and professional like a real F1 engineer.
Use real F1 radio language like 'box box', 'copy that', 'understood'.

Driver: {anomaly_row['Driver']}
Race: {anomaly_row.get('Race', 'Unknown')}
Lap: {int(anomaly_row['LapNumber'])}
Tire: {anomaly_row.get('Compound', 'Unknown')}
Deviation from baseline: {round((1 - anomaly_row['SeverityScore']) * 100, 1)}%

Generate the radio message:"""

    for attempt in range(retries):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.7
                },
                timeout=15
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            elif response.status_code == 429:
                wait = 2 ** attempt
                print(f"  Rate limited, retrying in {wait}s...")
                time.sleep(wait)
                continue
            else:
                return f"[Error {response.status_code}: {response.text[:100]}]"
        except requests.exceptions.Timeout:
            return "[Timeout: Groq API did not respond in 15s]"
        except Exception as e:
            return f"[Connection error: {e}]"

    return "[Failed after retries]"


# ---- Load anomaly data ----
anomaly_path = 'outputs/anomaly_report.csv'
if not os.path.exists(anomaly_path):
    raise FileNotFoundError(
        f"{anomaly_path} not found. Run 2_dna_model.py first."
    )

anomalies = pd.read_csv(anomaly_path)

required_cols = ['Driver', 'LapNumber', 'SeverityScore']
missing = [c for c in required_cols if c not in anomalies.columns]
if missing:
    raise ValueError(f"anomaly_report.csv is missing columns: {missing}")

for col, default in [('Race', 'Unknown'), ('Compound', 'Unknown'), ('LapTime_s', None)]:
    if col not in anomalies.columns:
        anomalies[col] = default

top_anomalies = anomalies.sort_values('SeverityScore').head(6)

print("Generating AI radio messages via Groq...\n")
print("=" * 60)

radio_messages = []

for _, row in top_anomalies.iterrows():
    msg = generate_radio_message(row.to_dict())

    radio_messages.append({
        'Driver'   : row['Driver'],
        'Race'     : row['Race'],
        'LapNumber': row['LapNumber'],
        'Compound' : row['Compound'],
        'Severity' : round((1 - row['SeverityScore']) * 100, 1),
        'RadioMsg' : msg
    })

    print(f"LAP {int(row['LapNumber'])} | {row['Driver']} | {row['Race']}")
    print(f"Severity: {round((1 - row['SeverityScore']) * 100, 1)}% off baseline")
    print(f"Radio: {msg}")
    print("-" * 60)

    time.sleep(0.3)

radio_df = pd.DataFrame(radio_messages)
radio_df.to_csv('outputs/radio_messages.csv', index=False)
print(f"\nDone! Saved to outputs/radio_messages.csv")
print("ENV PATH:", env_path)
print("KEY LOADED:", GROQ_API_KEY)