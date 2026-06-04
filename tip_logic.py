"""Diseña y VALIDA (contra el key real) la lógica del tip por-pregunta.

Combina el prior posicional (b/c son las más habituales) con la longitud
relativa, penalizando opciones con cuantificadores absolutos. Decide cuándo
nombrar UNA opción (alta confianza) o un PAR "b/c-style" (baja confianza).
Mide el acierto real para no auto-engañarnos.
"""
import json, re
from collections import Counter
import features as F

qs = F.load()
key = {int(k): v for k, v in json.load(open("key.json")).items()}
ans = {q["num"]: key[q["num"]] for q in qs}
N = len(qs)
LET = F.LETTERS
prior = {L: sum(1 for q in qs if ans[q["num"]] == L) / N for L in LET}

ABS = ["siempre","nunca","solo","solamente","todos","todas","ningun",
       "ninguna","exclusivamente","cualquier","unicamente"]
absre = re.compile(r"\b(" + "|".join(ABS) + r")\b")


def scores(q, w_len, abs_pen):
    """puntuación por opción = prior * (cuotaLongitud)^w_len * penalización."""
    opts = q["opciones"]
    lens = {L: len(v) for L, v in opts.items()}
    tot = sum(lens.values()) or 1
    sc = {}
    for L, v in opts.items():
        share = lens[L] / tot                      # ~0.25 si todas iguales
        pen = abs_pen if absre.search(F.norm(v)) else 1.0
        sc[L] = prior[L] * (share ** w_len) * pen
    s = sum(sc.values()) or 1
    return {L: sc[L] / s for L in sc}


def evaluate(w_len, abs_pen, gate):
    """top1: acierto nombrando 1; set: acierto del par cuando hay duda."""
    top1_hit = 0
    confident = unsure = 0
    conf_hit = 0
    set_hit = 0
    for q in qs:
        sc = scores(q, w_len, abs_pen)
        order = sorted(sc, key=lambda L: -sc[L])
        p1, p2 = sc[order[0]], sc[order[1]]
        if ans[q["num"]] == order[0]:
            top1_hit += 1
        if (p1 - p2) >= gate:                      # confianza para nombrar una
            confident += 1
            if ans[q["num"]] == order[0]:
                conf_hit += 1
        else:
            unsure += 1
            if ans[q["num"]] in (order[0], order[1]):
                set_hit += 1
    return {
        "top1": top1_hit / N,
        "confident_n": confident, "confident_acc": conf_hit / confident if confident else 0,
        "unsure_n": unsure, "set_acc": set_hit / unsure if unsure else 0,
    }


print(f"Prior posicional: " + " ".join(f"{L}={prior[L]:.0%}" for L in LET))
print(f"P(respuesta ∈ {{b,c}}) = {prior['b']+prior['c']:.0%}")
print(f"Baseline 'siempre la más larga' (chars): "
      f"{sum(1 for q in qs if max(q['opciones'], key=lambda L: len(q['opciones'][L]))==ans[q['num']])/N:.0%}\n")

print("Grid de parámetros (w_len, abs_pen) — acierto top-1:")
best = None
for w_len in [0.5, 1.0, 1.5, 2.0, 3.0]:
    for abs_pen in [1.0, 0.6, 0.4, 0.25]:
        r = evaluate(w_len, abs_pen, gate=0)
        if best is None or r["top1"] > best[0]:
            best = (r["top1"], w_len, abs_pen)
        print(f"  w_len={w_len:<4} abs_pen={abs_pen:<5} -> top1 {r['top1']:.1%}")
print(f"\nMejor top-1: {best[0]:.1%} con w_len={best[1]} abs_pen={best[2]}")

print("\nCon el mejor modelo, efecto del 'gate' (umbral p1-p2 para nombrar una sola):")
for gate in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]:
    r = evaluate(best[1], best[2], gate)
    print(f"  gate={gate:.2f}: nombra-una en {r['confident_n']:3d}/{N} (acierto {r['confident_acc']:.0%}) | "
          f"duda b/c-style en {r['unsure_n']:3d} (acierto del par {r['set_acc']:.0%})")
