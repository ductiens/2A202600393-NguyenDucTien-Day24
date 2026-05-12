import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pairwise = list(csv.DictReader((ROOT / "phase-b" / "pairwise_results.csv").open(encoding="utf-8")))
human = list(csv.DictReader((ROOT / "phase-b" / "human_labels.csv").open(encoding="utf-8")))
human_map = {r["id"]: r["human_winner"].upper() for r in human}

labels_judge = []
labels_human = []
for r in pairwise:
    if r["id"] in human_map:
        labels_judge.append(r["winner_after_swap"].upper())
        labels_human.append(human_map[r["id"]].replace("TIE", "TIE"))

def normalize(v: str) -> str:
    v = v.upper().strip()
    return v if v in {"A", "B", "TIE"} else "TIE"

labels_judge = [normalize(x) for x in labels_judge]
labels_human = [normalize(x) for x in labels_human]

def kappa(a, b):
    labels = ["A", "B", "TIE"]
    n = len(a)
    observed = sum(1 for x, y in zip(a, b) if x == y) / n if n else 0.0
    pe = 0.0
    for lb in labels:
        pa = sum(1 for x in a if x == lb) / n if n else 0.0
        pb = sum(1 for y in b if y == lb) / n if n else 0.0
        pe += pa * pb
    if abs(1 - pe) < 1e-12:
        return 1.0
    return (observed - pe) / (1 - pe)

score = kappa(labels_judge, labels_human)
if score < 0:
    interp = "poor"
elif score <= 0.20:
    interp = "slight"
elif score <= 0.40:
    interp = "fair"
elif score <= 0.60:
    interp = "moderate"
elif score <= 0.80:
    interp = "substantial"
else:
    interp = "almost perfect"

out = {
    "num_labeled_pairs": len(labels_judge),
    "cohen_kappa": round(score, 4),
    "interpretation": interp,
}
(ROOT / "phase-b" / "kappa_analysis_output.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(out)
