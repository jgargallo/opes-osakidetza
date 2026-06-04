"""Extracción de features por pregunta a partir de qa.json.

Dos tipos de "designadores de respuesta":
  - letra fija: a / b / c / d
  - selector:   la opción más corta / más larga / la que contiene cifra / la meta-opción

Dos tipos de "predicados" (definen el grupo de preguntas):
  - sobre el enunciado: longitud, paridad, palabra-clave, primera palabra, negación...
  - (los selectores no necesitan predicado: apuntan a la respuesta directamente)

Salida: para cada pregunta, un dict de features + los designadores aplicables.
"""
import json, re, unicodedata
from collections import Counter

LETTERS = ["a", "b", "c", "d"]


def norm(s):
    """minúsculas, sin tildes, solo para tokenizar palabras-clave."""
    s = s.lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return s


def words(text):
    return re.findall(r"\b\w+\b", norm(text))


def load(path="qa.json"):
    return json.load(open(path, encoding="utf-8"))


# ---------- designadores de respuesta (qué letra "elige" la heurística) ----------

def shortest_option(opts):
    """letra de la opción estrictamente más corta (None si hay empate)."""
    lens = {k: len(v) for k, v in opts.items()}
    m = min(lens.values())
    winners = [k for k, v in lens.items() if v == m]
    return winners[0] if len(winners) == 1 else None


def longest_option(opts):
    lens = {k: len(v) for k, v in opts.items()}
    m = max(lens.values())
    winners = [k for k, v in lens.items() if v == m]
    return winners[0] if len(winners) == 1 else None


META_RE = re.compile(norm(
    r"(todas las|todo lo anterior|ninguna de|todas las opciones|"
    r"a y b|b y c|son correctas|son falsas|son verdaderas)"))


def meta_option(opts):
    """letra de la (única) opción tipo 'todas/ninguna de las anteriores'."""
    hits = [k for k, v in opts.items() if META_RE.search(norm(v))]
    return hits[0] if len(hits) == 1 else None


def number_option(opts):
    """letra de la (única) opción que contiene una cifra."""
    hits = [k for k, v in opts.items() if re.search(r"\d", v)]
    return hits[0] if len(hits) == 1 else None


DESIGNATORS = {
    "MAS_CORTA": shortest_option,
    "MAS_LARGA": longest_option,
    "META_OPCION": meta_option,
    "OPCION_CON_CIFRA": number_option,
}


# ---------- predicados sobre el enunciado (definen grupos) ----------

NEG_WORDS = ["no", "falsa", "incorrecta", "excepto", "salvo", "nunca"]


def question_predicates(q, vocab_keywords):
    """devuelve set de predicados (strings) que cumple esta pregunta."""
    p = q["pregunta"]
    w = words(p)
    n = len(w)
    preds = set()

    # longitud (buckets y umbrales)
    preds.add(f"len>={(n//5)*5}")          # bucket de 5 en 5 (informativo)
    if n <= 15: preds.add("len<=15")
    if n >= 20: preds.add("len>=20")
    if n >= 30: preds.add("len>=30")
    if n >= 40: preds.add("len>=40")
    # paridad / módulo
    preds.add("npar" if n % 2 == 0 else "nimpar")
    preds.add(f"nmod3={n%3}")

    # primera palabra (categórica)
    if w:
        preds.add(f"empieza={w[0]}")

    # negación / tipo de pregunta
    if any(nw in w for nw in NEG_WORDS):
        preds.add("negativa")
    if "?" in p:
        preds.add("interrogacion")

    # palabras-clave (solo del vocabulario filtrado por frecuencia)
    for kw in vocab_keywords:
        if kw in w:
            preds.add(f"palabra={kw}")

    return preds


def build_vocab(questions, min_freq=5):
    """palabras que aparecen en >=min_freq enunciados (candidatas a regla)."""
    df = Counter()
    for q in questions:
        for tok in set(words(q["pregunta"])):
            df[tok] += 1
    return {w for w, c in df.items() if c >= min_freq}, df


def designator_letters(q):
    """para cada designador-selector, qué letra señala en esta pregunta."""
    out = {}
    for name, fn in DESIGNATORS.items():
        out[name] = fn(q["opciones"])
    return out


if __name__ == "__main__":
    qs = load()
    vocab, df = build_vocab(qs, min_freq=5)
    lens = [len(words(q["pregunta"])) for q in qs]
    import statistics as st
    print(f"Preguntas: {len(qs)}")
    print(f"Longitud enunciado (palabras): min={min(lens)} max={max(lens)} "
          f"media={st.mean(lens):.1f} mediana={st.median(lens)}")
    print(f"Vocabulario con freq>=5: {len(vocab)} palabras-clave candidatas")
    print("Top 25 palabras por nº de enunciados:")
    for w, c in df.most_common(25):
        print(f"   {c:3d}  {w}")
    # aplicabilidad de los designadores-selector
    print("\nAplicabilidad de selectores (cuántas preguntas tienen designador único):")
    for name, fn in DESIGNATORS.items():
        applic = sum(1 for q in qs if fn(q["opciones"]) is not None)
        print(f"   {name:18s}: {applic}/{len(qs)}")
