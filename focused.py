"""Análisis dirigido con el key real:
  1. Explotación del sesgo marginal (default + excepciones).
  2. Hipótesis pre-registradas sobre la estructura de las OPCIONES.
  3. Sesgos PROBABILÍSTICOS por subgrupo (skew fuerte aunque no puro),
     con test binomial y corrección por nº reducido de hipótesis.
"""
import json, math
from collections import Counter, defaultdict
import features as F

qs = F.load()
key = {int(k): v for k, v in json.load(open("key.json")).items()}
N = len(qs)
ans = {q["num"]: key[q["num"]] for q in qs}

marg = Counter(ans.values())
P = {L: marg[L] / N for L in F.LETTERS}


def binom_tail(k, n, p):
    """P(X>=k) con X~Binom(n,p): prob. de ver >=k aciertos por azar."""
    from math import comb
    return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))


print("="*72)
print("1. SESGO MARGINAL  (default + excepciones)")
print("="*72)
best = max(P, key=P.get)
hits = marg[best]
print(f"Marginal: " + "  ".join(f"{L}={marg[L]} ({P[L]:.0%})" for L in F.LETTERS))
print(f"Letra más frecuente: '{best}' con {hits}/{N} ({P[best]:.0%})")
print(f"Estrategia 'default={best}, memorizo el resto':")
print(f"   items = 1 regla + {N-hits} excepciones = {N-hits+1}  (vs {N})")
H = -sum(p*math.log2(p) for p in P.values())
print(f"Entropía de la respuesta: {H:.3f} bits (uniforme=2.000). "
      f"El sesgo ya 'regala' {2-H:.3f} bits.")


print("\n" + "="*72)
print("2. HIPÓTESIS PRE-REGISTRADAS (estructura de opciones)")
print("="*72)

def test_selector(name, fn, expect_correct=True):
    """fn(opts)->letra señalada. Mide P(correcta == señalada)."""
    appl = 0; hit = 0
    for q in qs:
        sel = fn(q["opciones"])
        if sel is None:
            continue
        appl += 1
        if ans[q["num"]] == sel:
            hit += 1
    if appl == 0:
        print(f"  {name}: no aplicable"); return
    rate = hit / appl
    # base de azar = prob. de acertar señalando esa posición segun marginal
    base = sum(P[fn(q['opciones'])] for q in qs if fn(q['opciones'])) / appl
    pv = binom_tail(hit, appl, base)
    flag = "  <-- ¿señal?" if pv < 0.01 else ""
    print(f"  {name:16s}: acierta {hit}/{appl} = {rate:.0%}  "
          f"(azar {base:.0%}, p={pv:.3f}){flag}")

print("H: 'elige la opción X' -> ¿con qué frecuencia acierta?")
for name, fn in F.DESIGNATORS.items():
    test_selector(name, fn)

# H: las opciones con cualificador absoluto, ¿son casi nunca correctas?
import re
ABS = ["siempre","nunca","solo","solamente","todos","todas","ningun",
       "ninguna","exclusivamente","cualquier"]
abs_re = re.compile(r"\b(" + "|".join(ABS) + r")\b")
abs_opts = 0; abs_correct = 0
for q in qs:
    for L, v in q["opciones"].items():
        if abs_re.search(F.norm(v)):
            abs_opts += 1
            if ans[q["num"]] == L:
                abs_correct += 1
print(f"\nH: opciones 'absolutas' (siempre/nunca/solo...) son falsas:")
print(f"   de {abs_opts} opciones absolutas, son la correcta {abs_correct} "
      f"({abs_correct/abs_opts:.0%}). Si fueran al azar: ~25%.")


print("\n" + "="*72)
print("3. SESGOS PROBABILÍSTICOS POR SUBGRUPO  (skew fuerte, aunque no puro)")
print("="*72)
print("Para cada predicado: distribución de respuestas dentro del grupo y")
print("si alguna letra domina muy por encima de su marginal (test binomial).")

vocab, _ = F.build_vocab(qs, min_freq=8)
preds_by_q = [F.question_predicates(q, vocab) for q in qs]
all_preds = set().union(*preds_by_q)

rows = []
for pred in all_preds:
    idx = [i for i in range(N) if pred in preds_by_q[i]]
    if len(idx) < 8:
        continue
    sub = Counter(ans[qs[i]["num"]] for i in idx)
    n = len(idx)
    L = max(sub, key=sub.get)
    k = sub[L]
    pv = binom_tail(k, n, P[L])      # ¿más L de lo esperado por marginal?
    rows.append((pv, pred, L, k, n, k/n))

rows.sort()
M_focus = len(rows)
print(f"\n(predicados evaluados: {M_focus}; umbral Bonferroni dirigido p<{0.05/M_focus:.4f})")
print(f"{'predicado':28s} {'->':2s} dom  k/n     %dom   p-valor   signif")
for pv, pred, L, k, n, frac in rows[:25]:
    sig = "***" if pv < 0.05/M_focus else ("*" if pv < 0.01 else "")
    print(f"{pred:28s}  {L}   {k:3d}/{n:<3d}  {frac:4.0%}   {pv:.5f}  {sig}")
