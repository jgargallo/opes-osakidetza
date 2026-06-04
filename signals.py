"""Búsqueda amplia de señales/sesgos en el banco (con key real).

A) SELECTORES relativos entre opciones: cada feature da una puntuación por
   opción; el selector elige argmax (o argmin). Medimos % de acierto vs azar
   con test binomial. Captura sesgos inconscientes del redactor.
B) SECUENCIA de respuestas: rachas, transiciones, autocorrelación
   (sesgos inconscientes tipo 'no repetir letra').
"""
import json, re, math
from collections import Counter
from math import comb
import features as F

qs = F.load()
key = {int(k): v for k, v in json.load(open("key.json")).items()}
seq = [key[q["num"]] for q in qs]            # secuencia ordenada 1..300
ans = {q["num"]: key[q["num"]] for q in qs}
N = len(qs)
P = {L: seq.count(L) / N for L in F.LETTERS}


def binom_tail(k, n, p):
    return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))


# --------- features escalares por opción (texto de la opción / vs enunciado) ---------
ABS = ["siempre","nunca","solo","solamente","todos","todas","ningun",
       "ninguna","exclusivamente","cualquier","unicamente"]
absre = re.compile(r"\b(" + "|".join(ABS) + r")\b")
STOP = set("de la el en y a los las del un una se que con por para su al lo "
           "como o e ni mas pero".split())


def wset(t):
    return set(w for w in F.words(t) if w not in STOP)


def option_scores(q):
    opts = q["opciones"]
    stem = wset(q["pregunta"])
    others = {L: wset(v) for L, v in opts.items()}
    sc = {}
    for L, v in opts.items():
        w = F.words(v); ws = others[L]
        # solapamiento medio con las OTRAS opciones (centralidad)
        cent = 0.0; cnt = 0
        for L2, w2 in others.items():
            if L2 == L: continue
            u = ws | w2
            cent += (len(ws & w2) / len(u)) if u else 0; cnt += 1
        sc[L] = {
            "len_chars": len(v),
            "len_words": len(w),
            "n_comas": v.count(","),
            "n_clausulas": len(re.findall(r"\b(que|cuando|donde|cuyo|cuya|si|aunque|"
                                          r"salvo|excepto|siempre que|mientras)\b", F.norm(v))),
            "overlap_stem": len(ws & stem),
            "overlap_stem_frac": (len(ws & stem) / len(ws)) if ws else 0,
            "centralidad": cent / cnt if cnt else 0,
            "tiene_y": int(bool(re.search(r"\by\b", F.norm(v)))),
            "tiene_o": int(bool(re.search(r"\bo\b", F.norm(v)))),
            "tiene_no": int(bool(re.search(r"\bno\b", F.norm(v)))),
            "tiene_cifra": int(bool(re.search(r"\d", v))),
            "tiene_absoluta": int(bool(absre.search(F.norm(v)))),
            "n_acronimos": len(re.findall(r"\b[A-Z]{2,}\b", v)),
            "n_mayus": len(re.findall(r"\b[A-Z][a-z]+", v)),
            "es_meta": int(bool(F.META_RE.search(F.norm(v)))),
        }
    return sc


# precompute
SC = [option_scores(q) for q in qs]
FEATS = list(SC[0]["a"].keys())


def eval_selector(feat, mode):
    """elige argmax/argmin de 'feat'; devuelve (acierto, aplicables, pv)."""
    hit = appl = 0
    base_sum = 0.0
    for i, q in enumerate(qs):
        vals = {L: SC[i][L][feat] for L in q["opciones"]}
        target = (max if mode == "max" else min)(vals.values())
        winners = [L for L, v in vals.items() if v == target]
        if len(winners) != 1:
            continue
        appl += 1
        pick = winners[0]
        base_sum += P[pick]
        if ans[q["num"]] == pick:
            hit += 1
    if appl < 20:
        return None
    base = base_sum / appl
    pv = binom_tail(hit, appl, base) if hit/appl > base else 1.0
    return hit, appl, hit/appl, base, pv


print("="*78)
print("A) SELECTORES RELATIVOS ENTRE OPCIONES (acierto vs azar, test binomial)")
print("="*78)
rows = []
for feat in FEATS:
    for mode in ("max", "min"):
        r = eval_selector(feat, mode)
        if r:
            rows.append((r[4], feat, mode, r[0], r[1], r[2], r[3]))
rows.sort()
M = len(rows)
print(f"(selectores evaluados: {M}; Bonferroni dirigido p<{0.05/M:.4f})")
print(f"{'feature':20s}{'modo':5s}{'acierto':>10s}{'azar':>7s}{'p-valor':>10s}  sig")
for pv, feat, mode, hit, appl, acc, base in rows[:20]:
    sig = "***" if pv < 0.05/M else ("**" if pv < 0.01 else ("*" if pv < 0.05 else ""))
    print(f"{feat:20s}{mode:5s}{hit:4d}/{appl:<4d}={acc:3.0%}{base:6.0%}{pv:10.5f}  {sig}")


# ------------------------------- B) SECUENCIA ---------------------------------
print("\n" + "="*78)
print("B) SECUENCIA DE RESPUESTAS (sesgos inconscientes del orden)")
print("="*78)

# rachas
runs = []
cur, ln = seq[0], 1
for x in seq[1:]:
    if x == cur: ln += 1
    else: runs.append(ln); cur, ln = x, 1
runs.append(ln)
rc = Counter(runs)
print("Distribución de longitudes de racha (misma letra seguida):")
for l in sorted(rc):
    print(f"   racha {l}: {rc[l]}")
# esperado bajo independencia con marginal P: P(racha continúa)=sum P_L^2
pcont = sum(p*p for p in P.values())
print(f"P(repetir letra) bajo independencia = {pcont:.3f}; "
      f"observado = {sum(1 for i in range(1,N) if seq[i]==seq[i-1])/(N-1):.3f}")

# matriz de transición: P(siguiente | actual)
print("\nMatriz de transición  P(siguiente | actual):")
print("        ->a    ->b    ->c    ->d")
for a in F.LETTERS:
    idx = [i for i in range(N-1) if seq[i] == a]
    nxt = Counter(seq[i+1] for i in idx)
    tot = len(idx)
    row = "  ".join(f"{(nxt.get(b,0)/tot if tot else 0):5.0%}" for b in F.LETTERS)
    print(f"   {a}: {row}   (n={tot})")
print(f"   (marginal global: " + " ".join(f"{L}={P[L]:.0%}" for L in F.LETTERS) + ")")

# ¿se evita repetir? test: nº de repeticiones observado vs esperado
reps = sum(1 for i in range(1, N) if seq[i] == seq[i-1])
exp_reps = (N-1) * pcont
# binomial: ¿menos repeticiones de lo esperado?
pv_less = sum(comb(N-1, i) * pcont**i * (1-pcont)**(N-1-i) for i in range(0, reps+1))
print(f"\nRepeticiones consecutivas: obs={reps}, esperado={exp_reps:.1f}. "
      f"P(<= obs por azar)={pv_less:.3f}")
if pv_less < 0.05:
    print("   -> SÍ hay supresión de repeticiones (sesgo inconsciente real).")
else:
    print("   -> no hay evidencia de supresión de repeticiones.")

# autocorrelación de letra (one-hot) a varios lags
print("\nAutocorrelación de la secuencia (¿la respuesta depende de las previas?):")
def onehot(x, L): return 1 if x == L else 0
for lag in [1, 2, 3]:
    # correlación media sobre letras
    cs = []
    for L in F.LETTERS:
        xs = [onehot(seq[i], L) for i in range(N)]
        mu = sum(xs)/N
        num = sum((xs[i]-mu)*(xs[i-lag]-mu) for i in range(lag, N))
        den = sum((x-mu)**2 for x in xs)
        cs.append(num/den if den else 0)
    print(f"   lag {lag}: autocorr media = {sum(cs)/len(cs):+.3f}")
