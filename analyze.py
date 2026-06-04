"""Minero de reglas para comprimir el banco de preguntas.

Una REGLA = (predicado P sobre el enunciado, designador G de respuesta).
  - G fijo:      predice siempre la misma letra (a/b/c/d) para el grupo P.
  - G selector:  predice la letra que señala una heurística sobre las opciones
                 (más corta, más larga, meta-opción, opción con cifra).

Una regla es PURA si acierta en TODAS las preguntas de su soporte.
Buscamos un conjunto pequeño de reglas puras de alta cobertura (set-cover
voraz en forma de lista de decisión ordenada). Lo que no cubra ninguna regla
son "excepciones" que hay que memorizar a pelo.

Control de azar: con M reglas candidatas, una regla pura que cubre k preguntas
solo es de fiar si  M * pvalue(k) < ALPHA  (corrección de Bonferroni).
Comparamos el resultado del key real contra keys ALEATORIOS (Monte Carlo):
ese es el "suelo de ruido" que hay que batir para que el método tenga sentido.
"""
import json, math, random, sys
from collections import Counter, defaultdict
import features as F

ALPHA = 0.05


def candidate_rules(questions, vocab):
    """Devuelve dos cosas:
       - preds_by_q[i] = set de predicados de la pregunta i
       - desig_by_q[i] = {nombre_selector: letra_o_None}
       - lista de (tipo, clave) de TODAS las reglas candidatas posibles.
    """
    preds_by_q, desig_by_q = [], []
    all_preds = set()
    for q in questions:
        p = F.question_predicates(q, vocab)
        preds_by_q.append(p)
        all_preds |= p
        desig_by_q.append(F.designator_letters(q))

    rules = []
    # fijas: cada predicado x cada letra
    for pred in all_preds:
        for L in F.LETTERS:
            rules.append(("FIX", pred, L))
    # selectores: globales (sin predicado) -> predicen la letra del selector
    for name in F.DESIGNATORS:
        rules.append(("SEL", None, name))
    # selectores condicionados a un predicado (más potentes y aún memorizables)
    for pred in all_preds:
        for name in F.DESIGNATORS:
            rules.append(("SEL", pred, name))
    return preds_by_q, desig_by_q, rules


def predicted_letter(rule, i, desig_by_q):
    """letra que la regla predice para la pregunta i, o None si no aplica."""
    typ, pred, key = rule
    if typ == "FIX":
        return key  # letra fija
    return desig_by_q[i].get(key)  # selector


def rule_support(rule, preds_by_q, desig_by_q):
    """índices de preguntas a las que la regla APLICA (predicado cumplido y
       designador definido)."""
    typ, pred, key = rule
    n = len(preds_by_q)
    sup = []
    for i in range(n):
        if pred is not None and pred not in preds_by_q[i]:
            continue
        if predicted_letter(rule, i, desig_by_q) is None:
            continue
        sup.append(i)
    return sup


def pvalue(rule, k, marg, sel_rate):
    """prob. de que la regla sea pura sobre k preguntas por azar."""
    typ, pred, key = rule
    if typ == "FIX":
        # grupo de tamaño k todo igual a ALGUNA letra (marginal empírica)
        return sum(p ** k for p in marg.values())
    else:
        return sel_rate[key] ** k


def mine(questions, key, vocab, verbose=True):
    """key: dict num->letra. Devuelve lista de decisión + excepciones."""
    preds_by_q, desig_by_q, rules = candidate_rules(questions, vocab)
    n = len(questions)
    ans = [key[q["num"]] for q in questions]

    marg = Counter(ans)
    marg = {L: marg.get(L, 0) / n for L in F.LETTERS}
    # tasa base de cada selector = P(acierto si las respuestas fueran ~ marginal)
    sel_rate = {}
    for name in F.DESIGNATORS:
        tot = sum(1 for i in range(n) if desig_by_q[i][name] is not None)
        rate = 0.0
        if tot:
            rate = sum(marg[desig_by_q[i][name]]
                       for i in range(n) if desig_by_q[i][name] is not None) / tot
        sel_rate[name] = rate

    M = len(rules)
    thr = ALPHA / M  # umbral Bonferroni por regla

    # reglas puras (aciertan en todo su soporte) y significativas
    pure = []
    for r in rules:
        sup = rule_support(r, preds_by_q, desig_by_q)
        if len(sup) < 2:
            continue
        if all(ans[i] == predicted_letter(r, i, desig_by_q) for i in sup):
            pv = pvalue(r, len(sup), marg, sel_rate)
            sig = (M * pv) < ALPHA
            pure.append((r, sup, pv, sig))

    sig_rules = [x for x in pure if x[3]]

    # ---- set-cover voraz (lista de decisión) usando solo reglas significativas
    covered = set()
    chosen = []
    pool = sorted(sig_rules, key=lambda x: -len(x[1]))
    while True:
        best, best_gain = None, 0
        for r, sup, pv, sig in pool:
            gain = len(set(sup) - covered)
            if gain > best_gain:
                best, best_gain = (r, sup, pv), gain
        if best is None or best_gain < 1:
            break
        chosen.append((best, best_gain))
        covered |= set(best[1])

    exceptions = n - len(covered)
    if verbose:
        report(questions, key, M, thr, pure, sig_rules, chosen,
               covered, exceptions, sel_rate, marg)
    return {
        "M": M, "n": n, "marginal": marg, "sel_rate": sel_rate,
        "n_pure": len(pure), "n_sig": len(sig_rules),
        "n_rules_used": len(chosen), "covered": len(covered),
        "exceptions": exceptions,
        "items_raw": n,                      # memorizar 300 respuestas
        "items_rules": len(chosen) + exceptions,  # reglas + excepciones
        "chosen": [(r[0], g) for r, g in chosen],
    }


def report(questions, key, M, thr, pure, sig, chosen, covered, exc, sel_rate, marg):
    print(f"\n{'='*70}\nRESULTADO DEL MINADO")
    print(f"{'='*70}")
    print(f"Marginal de respuestas: " +
          " ".join(f"{L}={p:.0%}" for L, p in marg.items()))
    print(f"Tasa selectores: " +
          " ".join(f"{k}={v:.0%}" for k, v in sel_rate.items()))
    print(f"Reglas candidatas (M): {M}  ->  umbral Bonferroni p<{thr:.2e}")
    print(f"Reglas PURAS (aciertan 100% su grupo): {len(pure)}")
    print(f"Reglas puras SIGNIFICATIVAS (baten el azar): {len(sig)}")
    print(f"\nLista de decisión elegida ({len(chosen)} reglas):")
    n = len(questions)
    for (r, g) in chosen:
        typ, pred, k = r[0]
        desc = f"[{pred}] -> {k}" if typ == "FIX" else \
               (f"-> {k}" if pred is None else f"[{pred}] -> {k}")
        print(f"   (+{g:3d})  {desc}")
    print(f"\nCobertura: {len(covered)}/{n}  | Excepciones a memorizar: {exc}")
    print(f"\n>>> COSTE DE MEMORIA <<<")
    print(f"    Sin método:  {n} respuestas")
    print(f"    Con método:  {len(chosen)} reglas + {exc} excepciones "
          f"= {len(chosen)+exc} items")
    if len(chosen) + exc < n:
        print(f"    Ahorro: {n-(len(chosen)+exc)} items "
              f"({100*(n-(len(chosen)+exc))/n:.0f}% menos)")
    else:
        print(f"    NO COMPRIME (el método no ayuda).")


def random_key(questions, seed, marg=None):
    rng = random.Random(seed)
    if marg is None:
        return {q["num"]: rng.choice(F.LETTERS) for q in questions}
    letters, weights = zip(*marg.items())
    return {q["num"]: rng.choices(letters, weights)[0] for q in questions}


def monte_carlo(questions, vocab, n_iter=30, marg=None):
    print(f"\n{'#'*70}\nMONTE CARLO: {n_iter} keys ALEATORIOS (suelo de ruido)")
    print(f"{'#'*70}")
    items, rules_used, covered = [], [], []
    for s in range(n_iter):
        k = random_key(questions, s, marg)
        res = mine(questions, k, vocab, verbose=False)
        items.append(res["items_rules"])
        rules_used.append(res["n_rules_used"])
        covered.append(res["covered"])
    import statistics as st
    n = len(questions)
    print(f"items a memorizar (reglas+excepc.):  "
          f"media={st.mean(items):.1f}  min={min(items)}  max={max(items)}  "
          f"(sin método = {n})")
    print(f"reglas significativas usadas:        "
          f"media={st.mean(rules_used):.1f}  max={max(rules_used)}")
    print(f"preguntas cubiertas por azar:        "
          f"media={st.mean(covered):.1f}  max={max(covered)}")
    print(f"\nINTERPRETACIÓN: con keys aleatorios y control de azar, este es el "
          f"\nahorro 'falso' esperable. El key REAL debe batirlo con holgura "
          f"\npara que el método tenga valor.")


if __name__ == "__main__":
    qs = F.load()
    vocab, _ = F.build_vocab(qs, min_freq=5)
    mode = sys.argv[1] if len(sys.argv) > 1 else "mc"

    if mode == "mc":
        # sin key real: caracterizar el suelo de ruido con keys uniformes
        monte_carlo(qs, vocab, n_iter=30)
    elif mode == "real":
        key = {int(k): v for k, v in json.load(open("key.json")).items()}
        mine(qs, key, vocab, verbose=True)
        # y comparamos contra el ruido manteniendo la MISMA marginal
        marg = Counter(key.values())
        tot = sum(marg.values())
        marg = {L: marg.get(L, 0) / tot for L in F.LETTERS}
        monte_carlo(qs, vocab, n_iter=30, marg=marg)
