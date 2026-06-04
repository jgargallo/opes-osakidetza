"""Genera docs/data.js con las 300 preguntas y todos los campos pre-calculados
que necesita la web (predicción de heurística, tags, tema, etc.).

Fuente única de la lógica de heurísticas: este script. El frontend solo pinta.
"""
import json, re, os
from collections import Counter
import features as F

qs = F.load()
key = {int(k): v for k, v in json.load(open("key.json")).items()}
N = len(qs)

ABS = ["siempre","nunca","solo","solamente","todos","todas","ningun",
       "ninguna","exclusivamente","cualquier","unicamente"]
absre = re.compile(r"\b(" + "|".join(ABS) + r")\b")


def has_abs(txt):
    return bool(absre.search(F.norm(txt)))


def longest_letter(opts):
    lens = {k: len(v) for k, v in opts.items()}
    m = max(lens.values())
    win = [k for k, v in lens.items() if v == m]
    return win[0] if len(win) == 1 else None


def heuristic_pred(opts):
    """La regla del proyecto: la más larga descartando las 'absolutas'."""
    cand = {k: len(v) for k, v in opts.items() if not has_abs(v)}
    if not cand:
        cand = {k: len(v) for k, v in opts.items()}
    m = max(cand.values())
    win = [k for k, v in cand.items() if v == m]
    return win[0]  # en empate, la primera (a<b<c<d)


THEMES = {
    "Profesiones sanitarias": ["profesion","sanitaria","sanitarias","colegiacion","facultativo"],
    "Plan de Salud Euskadi 2030": ["plan","euskadi","2030","objetivo","salud"],
    "Osakidetza": ["osakidetza"],
    "Incompatibilidades": ["incompatibilidad","incompatibilidades"],
    "Igualdad": ["igualdad","mujeres","hombres","genero"],
    "Normativa / leyes": ["ley","decreto","articulo","real","constitucion","estatuto","reglamento"],
    "Empleo público": ["personal","empleado","funcionario","servicio"],
}


def theme(q):
    w = set(F.words(q["pregunta"]))
    best, bs = "Otros", 0
    for name, kws in THEMES.items():
        s = sum(1 for k in kws if k in w)
        if s > bs:
            best, bs = name, s
    return best


def is_negative(q):
    w = F.words(q["pregunta"])
    return any(x in w for x in ["no","falsa","incorrecta","incorrectas","excepto","salvo"])


def letters_with_y(opts):
    """letras cuya opción enumera con «y» (señal fuerte de respuesta correcta)."""
    return [L for L, v in opts.items() if re.search(r"\by\b", F.norm(v))]


def most_commas(opts):
    """letra con estrictamente más comas (la más detallada), o None si empate."""
    cnt = {L: v.count(",") for L, v in opts.items()}
    m = max(cnt.values())
    if m == 0:
        return None
    win = [L for L, v in cnt.items() if v == m]
    return win[0] if len(win) == 1 else None


def first_word(q):
    w = F.words(q["pregunta"])
    return w[0] if w else ""


data = []
heur_ok = 0
for q in qs:
    opts = q["opciones"]
    correcta = key[q["num"]]
    pred = heuristic_pred(opts)
    ok = (pred == correcta)
    heur_ok += ok
    lon = longest_letter(opts)
    meta = F.meta_option(opts)
    abs_letters = [L for L, v in opts.items() if has_abs(v)]
    data.append({
        "num": q["num"],
        "pregunta": q["pregunta"],
        "opciones": opts,
        "correcta": correcta,
        "tema": theme(q),
        "heurPred": pred,
        "heurOk": ok,
        "longest": lon,
        "meta": meta,
        "neg": is_negative(q),
        "cual": first_word(q) == "cual",
        "absLetters": abs_letters,
        "optY": letters_with_y(opts),
        "comas": most_commas(opts),
    })

# estadísticas reales para la página de recursos
marg = Counter(key[q["num"]] for q in qs)
meta_info = {
    "n": N,
    "marginal": {L: marg.get(L, 0) for L in F.LETTERS},
    "heurAcc": round(100 * heur_ok / N),
    "heurFails": [d["num"] for d in data if not d["heurOk"]],
    "themes": dict(Counter(d["tema"] for d in data)),
    # números medidos en el análisis (signals.py / focused.py)
    "stats": {
        "azar": 25, "siempreB": 32, "masLarga": 40, "masLargaSinAbs": 43,
        "tieneY": 59, "masComas": 48, "absolutaCorrecta": 17, "techoML": 44,
    },
}

os.makedirs("docs", exist_ok=True)
with open("docs/data.js", "w", encoding="utf-8") as f:
    f.write("// Generado por build_site_data.py — no editar a mano\n")
    f.write("window.QA = " + json.dumps(data, ensure_ascii=False) + ";\n")
    f.write("window.QA_META = " + json.dumps(meta_info, ensure_ascii=False) + ";\n")

print(f"docs/data.js generado: {N} preguntas.")
print(f"Heurística (más larga sin absolutas) acierta: {heur_ok}/{N} = {100*heur_ok/N:.0f}%")
print(f"Preguntas donde la heurística FALLA (trampas): {len(meta_info['heurFails'])}")
