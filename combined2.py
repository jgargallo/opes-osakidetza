"""Techo combinado v2: features RELATIVAS dentro de cada pregunta.
Para cada feature escalar de la opción se calcula su z-score respecto a las
4 hermanas + indicadores es_max/es_min. Así el modelo puede aprender
'la más larga / la que tiene y / la no-absoluta'. CV honesta por pregunta.
"""
import json
import numpy as np
from collections import Counter
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
import features as F
import signals as S

qs = F.load()
key = {int(k): v for k, v in json.load(open("key.json")).items()}
ans = {q["num"]: key[q["num"]] for q in qs}
N = len(qs); LET = F.LETTERS
NUM_FEATS = [f for f in S.FEATS]  # todas son numéricas/binarias

X, y, groups, meta = [], [], [], []
for i, q in enumerate(qs):
    opts = list(q["opciones"].keys())
    # matriz feature x opción para esta pregunta
    vals = {f: np.array([S.SC[i][L][f] for L in opts], float) for f in NUM_FEATS}
    for j, L in enumerate(opts):
        row = []
        for f in NUM_FEATS:
            v = vals[f]; mu = v.mean(); sd = v.std()
            z = (v[j] - mu) / sd if sd > 0 else 0.0
            is_max = 1.0 if v[j] == v.max() and (v == v.max()).sum() == 1 else 0.0
            is_min = 1.0 if v[j] == v.min() and (v == v.min()).sum() == 1 else 0.0
            row += [z, is_max, is_min]
        X.append(row); y.append(1 if ans[q["num"]] == L else 0)
        groups.append(i); meta.append((i, L))
X = np.array(X); y = np.array(y); groups = np.array(groups)

gkf = GroupKFold(n_splits=10)
proba = np.zeros(len(y))
for tr, te in gkf.split(X, y, groups):
    clf = LogisticRegression(max_iter=3000, C=0.5)
    clf.fit(X[tr], y[tr])
    proba[te] = clf.predict_proba(X[te])[:, 1]

by_q = {}
for p, (i, L) in zip(proba, meta):
    by_q.setdefault(i, []).append((p, L))
correct = sum(1 for i, lst in by_q.items() if ans[qs[i]["num"]] == max(lst)[1])

print("="*70)
print("TECHO COMBINADO v2 (features relativas, CV honesta 10-fold)")
print("="*70)
print(f"Precisión modelo combinado (CV):  {correct}/{N} = {correct/N:.1%}")
print(f"  azar 25%  |  siempre-b {Counter(ans.values()).most_common(1)[0][1]/N:.0%}"
      f"  |  más-larga-sin-abs 43%")
