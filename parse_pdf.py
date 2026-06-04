"""Parser del banco de preguntas qa.pdf -> qa.json

Estructura del PDF:
  N.-   <enunciado, multilínea>
  a)    <opción a, multilínea>
  b)    ...
  c)    ...
  d)    ...
"""
import fitz, re, json, sys

PDF = "qa.pdf"
OUT = "qa.json"


def full_text(path):
    doc = fitz.open(path)
    return "\n".join(doc[i].get_text() for i in range(doc.page_count))


def clean(s):
    # colapsa espacios/saltos en un único espacio
    return re.sub(r"\s+", " ", s).strip()


def parse(text):
    # marcador de pregunta: inicio de línea, número y ".-"
    q_re = re.compile(r"(?m)^[ \t]*(\d+)\.?-[ \t]*$")
    matches = list(q_re.finditer(text))
    questions = []
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        # localizar opciones a) b) c) d) a inicio de línea
        opt_re = re.compile(r"(?m)^[ \t]*([a-d])\)[ \t]*")
        opts = list(opt_re.finditer(block))
        if not opts:
            # pregunta sin opciones detectadas: guardar para inspección
            questions.append({"num": num, "pregunta": clean(block),
                              "opciones": {}, "_warn": "sin_opciones"})
            continue

        enunciado = clean(block[:opts[0].start()])
        options = {}
        for j, om in enumerate(opts):
            letter = om.group(1)
            o_start = om.end()
            o_end = opts[j + 1].start() if j + 1 < len(opts) else len(block)
            options[letter] = clean(block[o_start:o_end])

        questions.append({
            "num": num,
            "pregunta": enunciado,
            "opciones": options,
        })
    return questions


def main():
    text = full_text(PDF)
    qs = parse(text)
    # diagnóstico
    n = len(qs)
    nums = [q["num"] for q in qs]
    dups = [x for x in set(nums) if nums.count(x) > 1]
    weird = [q for q in qs if len(q.get("opciones", {})) != 4]
    print(f"Preguntas detectadas: {n}")
    print(f"Rango numeración: {min(nums)}..{max(nums)}")
    print(f"Números duplicados: {dups[:20]}")
    print(f"Preguntas sin exactamente 4 opciones: {len(weird)}")
    for q in weird[:10]:
        print("  -> nº", q["num"], "opciones:", list(q.get("opciones", {}).keys()),
              "| enun:", q["pregunta"][:60])
    # comprobar secuencia consecutiva
    expected = list(range(min(nums), max(nums) + 1))
    missing = sorted(set(expected) - set(nums))
    print(f"Números faltantes en la secuencia: {missing[:30]}")

    json.dump(qs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nGuardado -> {OUT}")


if __name__ == "__main__":
    main()
