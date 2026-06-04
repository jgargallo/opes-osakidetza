"""Techo combinado: ¿cuánto acierto se logra juntando TODAS las señales,
medido con validación cruzada honesta (sin sobreajuste)?

Modelo a nivel de OPCIÓN: features de cada opción -> P(ser la correcta).
Para cada pregunta se elige la opción con mayor probabilidad.
GroupKFold por pregunta: ninguna opción de una pregunta de test se ha visto
en entrenamiento -> la precisión reportada es generalizable.
"""
import json, re
import numpy as np
from collections import Counter
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
import features as F
import signals as S   # reutiliza SC (scores por opción) y FEATS

qs = F.load()
key = {int(k): v for k, v in json.load(open("key.json")).items()}
ans = {q["num"]: key[q["num"]] for q in qs}
N = len(qs)
LET = F.LETTERS

# matriz a nivel opción
X, y, groups, meta = [], [], [], []
for i, q in enumerate(qs):
    for L in q["opciones"]:
        feats = S.SC[i][L]
        X.append([feats[f] for f in S.FEATS])
        y.append(1 if ans[q["num"]] == L else 0)
        groups.append(i)
        meta.append((i, L))
X = np.array(X, float); y = np.array(y); groups = np.array(groups)
# normaliza columnas
mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
Xn = (X - mu) / sd

gkf = GroupKFold(n_splits=5)
proba = np.zeros(len(y))
for tr, te in gkf.split(Xn, y, groups):
    clf = LogisticRegression(max_iter=2000, C=1.0)
    clf.fit(Xn[tr], y[tr])
    proba[te] = clf.predict_proba(Xn[te])[:, 1]

# precisión: por pregunta, elegir opción con mayor proba (CV out-of-fold)
correct = 0
by_q = {}
for p, (i, L) in zip(proba, meta):
    by_q.setdefault(i, []).append((p, L))
for i, lst in by_q.items():
    pick = max(lst)[1]
    if ans[qs[i]["num"]] == pick:
        correct += 1

print("="*70)
print("TECHO COMBINADO (validación cruzada honesta por pregunta)")
print("="*70)
print(f"Precisión modelo combinado (CV):  {correct}/{N} = {correct/N:.1%}")
print(f"  Referencia azar puro:           25%")
print(f"  Referencia 'siempre b':         {Counter(ans.values()).most_common(1)[0][1]/N:.1%}")
print(f"  Referencia 'más larga sin abs': 43%")

# importancia de features (modelo entrenado en todo, solo para leer signos)
clf = LogisticRegression(max_iter=2000).fit(Xn, y)
imp = sorted(zip(S.FEATS, clf.coef_[0]), key=lambda t: -abs(t[1]))
print("\nPeso de cada señal (signo + = favorece ser correcta):")
for f, c in imp:
    arrow = "↑correcta" if c > 0 else "↓distractora"
    print(f"   {f:18s} {c:+.2f}  {arrow}")
