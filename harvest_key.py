"""Extrae el key de respuestas correctas sondeando kaixo.com.

Para cada pregunta, prueba A,B,C,D hasta que el servidor responde
"Correctas: 1". Respeta el servidor con un retardo entre peticiones.
Stateless: no reutiliza cookie de sesión, así el contador refleja solo
la respuesta enviada.
"""
import urllib.parse, re, json, time, sys, subprocess

BASE = "https://www.kaixo.com/opeosaki/index.php"
AUKERA = "ope26osakicomun300"
DELAY = 0.4          # segundos entre peticiones
LETTERS = ["A", "B", "C", "D"]
CORRECT_RE = re.compile(r"Correctas:<font color=blue>\s*1\s*</font>")
HEADERS = {"User-Agent": "Mozilla/5.0 (study-tool; personal use)"}


def probe(idpregunta, opcion):
    """True si 'opcion' es la correcta para 'idpregunta'."""
    params = urllib.parse.urlencode({
        "aukera": AUKERA, "hizk": "1", "num": idpregunta,
        "idpregunta": idpregunta, "opcion": opcion, "tema": "", "eranmota": "",
    })
    url = f"{BASE}?{params}"
    for attempt in range(3):
        try:
            # curl verifica TLS con el almacén de confianza del sistema
            out = subprocess.run(
                ["curl", "-s", "--fail", "-A", HEADERS["User-Agent"], url],
                capture_output=True, text=True, timeout=25)
            if out.returncode == 0:
                return bool(CORRECT_RE.search(out.stdout))
        except Exception:
            pass
        if attempt == 2:
            raise RuntimeError(f"fallo al consultar Q{idpregunta} opcion {opcion}")
        time.sleep(1.0)


def harvest(ids, out="key.json"):
    key = {}
    try:
        key = {int(k): v for k, v in json.load(open(out)).items()}
    except Exception:
        pass
    n_req = 0
    for qid in ids:
        if qid in key and key[qid]:
            continue
        found = None
        for L in LETTERS:
            n_req += 1
            if probe(qid, L):
                found = L
                break
            time.sleep(DELAY)
        time.sleep(DELAY)
        key[str(qid)] = found.lower() if found else None
        json.dump(key, open(out, "w"), ensure_ascii=False, indent=0)
        status = found if found else "??? (sin correcta marcada)"
        print(f"  Q{qid:3d} -> {status}   [peticiones acum: {n_req}]", flush=True)
    # normaliza claves a int-string ordenado
    norm = {str(k): key[str(k)] if str(k) in key else key.get(k)
            for k in sorted(int(x) for x in key)}
    json.dump(norm, open(out, "w"), ensure_ascii=False, indent=0)
    done = sum(1 for v in norm.values() if v)
    print(f"\nHecho: {done}/{len(norm)} respuestas. Peticiones totales: {n_req}")
    miss = [k for k, v in norm.items() if not v]
    if miss:
        print(f"Sin respuesta marcada en el servidor: {miss}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        ids = [1, 2, 3]
    else:
        ids = range(1, 301)
    harvest(ids)
