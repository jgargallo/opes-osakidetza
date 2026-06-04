"""Análisis exploratorio del banco (SIN key de respuestas).

Busca estructura que (a) ayude a memorizar aunque no prediga la letra, y
(b) patrones DENTRO de las opciones que podrían insinuar la respuesta y que
validaremos en cuanto tengamos el key.
"""
import json, re, unicodedata
from collections import Counter, defaultdict
import features as F

qs = F.load()
N = len(qs)


def hist(values, width=50, bins=None):
    c = Counter(values)
    keys = bins if bins else sorted(c)
    mx = max(c.values()) if c else 1
    for k in keys:
        v = c.get(k, 0)
        bar = "#" * int(width * v / mx)
        print(f"   {str(k):>8} | {bar} {v}")


# ---------------------------------------------------------------- 1. LONGITUDES
print("="*72)
print("1. LONGITUD DEL ENUNCIADO (palabras)")
print("="*72)
qlen = [len(F.words(q["pregunta"])) for q in qs]
hist([(l // 10) * 10 for l in qlen], bins=[0,10,20,30,40,50,60,70])
print(f"   min={min(qlen)} max={max(qlen)} media={sum(qlen)/N:.1f}")

print("\n   Longitud de las OPCIONES (palabras) — todas juntas:")
olen = [len(F.words(v)) for q in qs for v in q["opciones"].values()]
hist([(l // 10) * 10 for l in olen], bins=[0,10,20,30,40,50,60])
print(f"   min={min(olen)} max={max(olen)} media={sum(olen)/len(olen):.1f}")


# -------------------------------------------------- 2. POSICIÓN OPCIÓN MÁS LARGA/CORTA
print("\n" + "="*72)
print("2. ¿DÓNDE CAE LA OPCIÓN MÁS LARGA / MÁS CORTA? (clave si hay heurística)")
print("="*72)
def pos_extremo(fn_cmp):
    pos = []
    for q in qs:
        lens = {k: len(v) for k, v in q["opciones"].items()}
        target = fn_cmp(lens.values())
        winners = [k for k, v in lens.items() if v == target]
        pos.append(winners[0] if len(winners) == 1 else "empate")
    return pos

print("Opción MÁS LARGA por posición:")
hist(pos_extremo(max), bins=["a","b","c","d","empate"])
print("\nOpción MÁS CORTA por posición:")
hist(pos_extremo(min), bins=["a","b","c","d","empate"])

# margen: ¿cuánto destaca la más larga sobre la segunda?
margins = []
for q in qs:
    lens = sorted((len(v) for v in q["opciones"].values()), reverse=True)
    if lens[1] > 0:
        margins.append(lens[0] / lens[1])
print(f"\nMargen long(1ª)/long(2ª más larga): media={sum(margins)/len(margins):.2f}")
big = sum(1 for m in margins if m >= 1.5)
print(f"   Preguntas donde la más larga destaca >=1.5x sobre la 2ª: {big}/{N}")


# ----------------------------------------------------- 3. META-OPCIONES Y SU POSICIÓN
print("\n" + "="*72)
print("3. META-OPCIONES ('todo/todas/ninguna de las anteriores', 'a y b'...)")
print("="*72)
meta_pos = []
for q in qs:
    for k, v in q["opciones"].items():
        if F.META_RE.search(F.norm(v)):
            meta_pos.append(k)
print(f"Total meta-opciones encontradas: {len(meta_pos)} (en {N} preguntas)")
hist(meta_pos, bins=["a","b","c","d"])
# casi siempre en d?
print("   (clásico: suelen ir en 'd'; si la correcta tiende a la meta-opción, es oro)")


# --------------------------------------------------- 4. PALABRAS ABSOLUTAS EN OPCIONES
print("\n" + "="*72)
print("4. CUALIFICADORES ABSOLUTOS EN OPCIONES ('siempre','nunca','solo','todo')")
print("="*72)
ABS = ["siempre", "nunca", "solo", "solamente", "todos", "todas", "ningun",
       "ninguna", "exclusivamente", "cualquier"]
abs_re = re.compile(r"\b(" + "|".join(ABS) + r")\b")
cnt_abs = Counter()
q_with_abs = 0
for q in qs:
    has = False
    for k, v in q["opciones"].items():
        if abs_re.search(F.norm(v)):
            cnt_abs[k] += 1; has = True
    if has: q_with_abs += 1
print(f"Preguntas con alguna opción 'absoluta': {q_with_abs}/{N}")
print("Distribución por posición:")
hist(cnt_abs, bins=["a","b","c","d"])


# -------------------------------------------------- 5. OPCIONES QUE COMPARTEN PREFIJO
print("\n" + "="*72)
print("5. OPCIONES PARAFRASEADAS (varias comparten arranque -> 'odd one out')")
print("="*72)
def shared_prefix_words(a, b):
    wa, wb = F.words(a), F.words(b)
    n = 0
    for x, y in zip(wa, wb):
        if x == y: n += 1
        else: break
    return n

share_count = 0
for q in qs:
    opts = list(q["opciones"].values())
    pref = max(shared_prefix_words(opts[i], opts[j])
               for i in range(4) for j in range(i+1, 4))
    if pref >= 3:
        share_count += 1
print(f"Preguntas donde >=2 opciones comparten >=3 palabras iniciales: {share_count}/{N}")
print("   (en estos casos la correcta suele ser la 'distinta' o la más completa)")


# ------------------------------------------------------- 6. TIPO DE PREGUNTA (enunciado)
print("\n" + "="*72)
print("6. TIPO DE ENUNCIADO")
print("="*72)
neg = sum(1 for q in qs if any(w in F.words(q["pregunta"])
          for w in ["no","falsa","incorrecta","excepto","salvo"]))
inter = sum(1 for q in qs if "?" in q["pregunta"])
print(f"   Negativas (NO/falsa/incorrecta/excepto): {neg}/{N}")
print(f"   Interrogativas (con '?'):                {inter}/{N}")
print("   Primera palabra del enunciado (top 12):")
first = Counter(F.words(q["pregunta"])[0] for q in qs if F.words(q["pregunta"]))
for w, c in first.most_common(12):
    print(f"      {c:3d}  {w}")


# ----------------------------------------------- 7. FAMILIAS DE PREGUNTAS CASI IGUALES
print("\n" + "="*72)
print("7. PREGUNTAS CASI DUPLICADAS / FAMILIAS (Jaccard sobre enunciado+opciones)")
print("="*72)
def bag(q):
    s = q["pregunta"] + " " + " ".join(q["opciones"].values())
    return set(F.words(s))
bags = [bag(q) for q in qs]

parent = list(range(N))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b):
    parent[find(a)] = find(b)

TH = 0.55
pairs = 0
for i in range(N):
    for j in range(i+1, N):
        inter_ = len(bags[i] & bags[j])
        uni = len(bags[i] | bags[j])
        if uni and inter_/uni >= TH:
            union(i, j); pairs += 1
clusters = defaultdict(list)
for i in range(N):
    clusters[find(i)].append(i)
fams = [c for c in clusters.values() if len(c) >= 2]
print(f"Pares muy similares (Jaccard>={TH}): {pairs}")
print(f"Familias (>=2 preguntas casi iguales): {len(fams)}  "
      f"que agrupan {sum(len(c) for c in fams)} preguntas")
fams.sort(key=len, reverse=True)
for c in fams[:8]:
    nums = [qs[i]["num"] for i in c]
    print(f"   familia {nums}: {qs[c[0]]['pregunta'][:70]}")


# --------------------------------------------------------------- 8. BLOQUES TEMÁTICOS
print("\n" + "="*72)
print("8. BLOQUES TEMÁTICOS (palabra-tema dominante por pregunta, en orden)")
print("="*72)
THEMES = {
    "sanitaria/profesiones": ["profesion","sanitaria","colegiacion","facultativo"],
    "Plan Salud Euskadi": ["plan","euskadi","salud","2030","objetivo"],
    "Osakidetza": ["osakidetza"],
    "Ley/Decreto/normativa": ["ley","decreto","articulo","real","constitucion","estatuto"],
    "incompatibilidades": ["incompatibilidad","incompatibilidades","53"],
    "personal/empleo público": ["personal","empleado","funcionario","servicio"],
}
def theme(q):
    w = set(F.words(q["pregunta"]))
    best, bs = "otros", 0
    for name, kws in THEMES.items():
        s = sum(1 for k in kws if k in w)
        if s > bs: best, bs = name, s
    return best
seq = [theme(q) for q in qs]
print("Recuento por tema:")
for t, c in Counter(seq).most_common():
    print(f"   {c:3d}  {t}")
# rachas (¿el examen va por bloques?)
runs = []
cur = seq[0]; ln = 1
for t in seq[1:]:
    if t == cur: ln += 1
    else: runs.append((cur, ln)); cur, ln = t, 1
runs.append((cur, ln))
long_runs = [r for r in runs if r[1] >= 4]
print(f"\nRachas consecutivas del mismo tema (>=4 seguidas): {len(long_runs)}")
for t, l in long_runs[:15]:
    print(f"   {l:2d} seguidas -> {t}")
