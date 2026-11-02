"""Monthly mean of Da Nang daily maximum apparent temperature."""
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/scoring/derived/climate_danang.json"


def fetch_climate():
    params = dict(latitude=16.05, longitude=108.2, start_date="2023-01-01",
                  end_date="2025-12-31", daily="apparent_temperature_max", timezone="Asia/Bangkok")
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bangeoreum-research/0.1"})
        with urllib.request.urlopen(req, timeout=120) as response:
            daily = json.load(response)["daily"]
        values = defaultdict(list)
        for day, value in zip(daily["time"], daily["apparent_temperature_max"]):
            if value is not None:
                values[int(day[5:7])].append(value)
        if len(values) != 12:
            return None
        result = {"source": url, "period": "2023-01-01..2025-12-31",
                  "monthly_mean_apparent_max_c": {str(m): round(sum(values[m]) / len(values[m]), 2) for m in range(1, 13)}}
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    except (OSError, ValueError, KeyError, TypeError):
        return None
