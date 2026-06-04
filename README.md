# ¿Se puede "hackear" un test de oposición sin estudiar?

### Un análisis estadístico de la batería común (300 preguntas) de la OPE Osakidetza 2026

> **TL;DR** — Analizamos las 300 preguntas y sus respuestas buscando reglas que permitieran
> *memorizar menos*. El texto de la pregunta **no predice** la respuesta (lo demostramos con
> control de azar). El único sesgo real está en **cómo se redactan las opciones**: la correcta
> tiende a ser la **más larga, completa y matizada**. Una regla simple acierta el **43 %** (vs 25 %
> del azar), y un modelo de ML validado no sube de **~44 %**. No hay atajo para memorizar, pero sí
> una heurística sólida para las preguntas que no te sepas.
>
> 🌐 **App de estudio:** **https://jgargallo.github.io/opes-osakidetza/**

---

## Resumen (abstract)

Las metodologías populares de "memorización por patrones" en oposiciones asumen que existen
reglas del tipo *"si la pregunta contiene la palabra X, la respuesta es la Y"*. Sometemos esa
hipótesis a prueba sobre un corpus fijo de **300 preguntas tipo test** con respuesta conocida.
Formalizamos el problema como **compresión de un conjunto de datos fijo** (no como predicción
generalizable) y mostramos que, bajo control de comparaciones múltiples (Bonferroni) y un modelo
nulo de Monte Carlo, **ninguna regla basada en el texto del enunciado supera el azar**. En cambio,
las características **relativas entre opciones** (longitud, enumeración con «y», nº de comas,
ausencia de cuantificadores absolutos) sí presentan sesgos altamente significativos. Un modelo de
regresión logística con validación cruzada por pregunta alcanza un techo de **43,7 %** de acierto,
indistinguible de una heurística de una sola línea. Concluimos que el examen no es "memorizable"
por reglas del enunciado, pero exhibe el sesgo clásico de los tests mal diseñados: *la opción
correcta es la más elaborada.*

---

## 1. Motivación

En la preparación de oposiciones es común memorizar las respuestas "sin entenderlas". La pregunta
de investigación fue del propio opositor:

> *¿Existen patrones en el texto que permitan agrupar preguntas de forma que, dentro de cada grupo,
> la respuesta sea siempre la misma — reduciendo así lo que hay que memorizar?*

Y, de forma crítica:

> *Aunque el orden de la respuesta correcta fuese aleatorio, en un conjunto fijo de 300 preguntas,
> ¿no podríamos encontrar coincidencias que lo hicieran más fácil por azar?*

Este repositorio responde ambas con datos.

---

## 2. Datos

| | |
|---|---|
| **Corpus** | 300 preguntas, batería común categorías C2/C3/D/E |
| **Opciones** | 4 por pregunta (a/b/c/d) |
| **Fuente del enunciado** | `qa.pdf` (99 páginas) |
| **Fuente de las respuestas** | kaixo.com (test online) — ⚠️ **orientativas, no oficiales** |

### 2.1 Extracción de las preguntas (`parse_pdf.py`)

El PDF tiene una estructura regular (`N.-` para el enunciado, `a)…d)` para las opciones).
Un parser con expresiones regulares produce `qa.json` con las 300 preguntas. Validación: secuencia
1–300 completa, sin duplicados, exactamente 4 opciones cada una (tras corregir un marcador
malformado, `195-` en vez de `195.-`).

### 2.2 Extracción del key de respuestas (`harvest_key.py`)

La web corrige **en el servidor**: al enviar una opción devuelve solo un contador de
aciertos/fallos, sin revelar la correcta en el HTML. Aprovechamos que el contador *filtra* la
respuesta: para cada pregunta se prueban A→D hasta obtener "Correcta", de forma educada
(retardo entre peticiones, verificación TLS con el almacén del sistema). Resultado: `key.json`
con las 300 respuestas (717 peticiones).

---

## 3. Métodos

### 3.1 Marco teórico: compresión, no predicción

Como el examen reutiliza **el texto y el orden exactos**, no necesitamos generalizar a preguntas
nuevas. El objetivo real es **comprimir**: hallar un conjunto de reglas tal que
`#reglas + #excepciones ≪ 300`. Esto evita el espejismo del *machine learning predictivo* y centra
el problema en la teoría de la información.

### 3.2 El riesgo de azar y su control

Un grupo de `k` preguntas es "puro" (todas la misma letra) por azar con probabilidad
`(1/4)^(k-1)`. Con `M` reglas candidatas, el grupo puro más grande esperable por azar es
`k ≈ 1 + log(M)/log(4)`. Controlamos las comparaciones múltiples con **Bonferroni**
(`M · p < 0,05`) y caracterizamos el suelo de ruido con **Monte Carlo** (keys aleatorios sometidos
al mismo pipeline).

### 3.3 Minado de reglas del enunciado (`analyze.py`, `features.py`)

`M = 2.268` reglas candidatas combinando predicados del enunciado (longitud, paridad, módulos,
primera palabra, negación, 230 palabras-clave) con designadores de respuesta (letra fija o
selectores como "la más corta/larga").

### 3.4 Señales relativas entre opciones (`signals.py`, `focused.py`)

23 selectores que puntúan cada opción y eligen el argmax/argmin: longitud, nº de comas, cláusulas
subordinadas, solapamiento léxico con el enunciado, centralidad respecto a las otras opciones,
presencia de «y/o/no», cifras, acrónimos y cuantificadores absolutos. Cada uno se evalúa con un
**test binomial** contra su tasa base.

### 3.5 Análisis de la secuencia (`signals.py`)

Tratamos las 300 respuestas como una serie temporal: distribución de rachas, matriz de transición
`P(siguiente | actual)`, supresión de repeticiones y autocorrelación a varios lags — para detectar
sesgos inconscientes del tipo "no repetir letra".

### 3.6 Modelo combinado (`combined2.py`)

Regresión logística a nivel de **opción** (features relativas dentro de cada pregunta: z-score e
indicadores es_max/es_min), eligiendo por pregunta la opción con mayor probabilidad. Precisión
medida con **GroupKFold** (10 folds) agrupando por pregunta → ninguna opción de test se ve en
entrenamiento, así que la cifra es **honesta (no sobreajustada)**.

---

## 4. Resultados

### 4.1 La marginal NO es uniforme

| a | b | c | d |
|:-:|:-:|:-:|:-:|
| 65 (22 %) | **96 (32 %)** | **90 (30 %)** | 49 (16 %) |

Entropía = 1,952 bits (uniforme = 2,000). «b»+«c» = 62 %; la «d» es la más rara.

### 4.2 El texto del enunciado NO predice (resultado central)

| | Reglas significativas | Compresión | Items a memorizar |
|---|:-:|:-:|:-:|
| **Key real** | **0** / 2.268 | ninguna | 300 |
| Keys aleatorios (Monte Carlo) | 0 | ninguna | 300 |

El key real se comporta **igual que el azar**. No existen reglas deterministas del enunciado:
la idea original de "agrupar para memorizar menos" **no es viable** en este examen.

### 4.3 Sí hay sesgo en las OPCIONES (test binomial)

| Señal (elige la opción…) | Acierto | Azar | Signif. |
|---|:-:|:-:|:-:|
| …que contiene «y» (enumera) | **59 %** | 27 % | *** |
| …con más comas | 48 % | 25 % | *** |
| …más larga | 40 % | 26 % | *** |
| …no-absoluta (cuando 3 sí lo son) | 75 % (n=20) | 26 % | *** |
| …con más cláusulas subordinadas | 42 % | 27 % | ** |
| Opciones con «siempre/nunca/solo» → correctas solo | 17 % | 25 % | — |

Todas apuntan a lo mismo: **la respuesta correcta es la más larga, completa y matizada**; los
distractores son más cortos y tajantes.

### 4.4 La secuencia no aporta señal explotable

Sin supresión de repeticiones significativa (p = 0,12) ni autocorrelación relevante
(lag-1 = −0,04). Curiosidad real (confirmada): una racha de **12 respuestas «b» seguidas**
(preguntas 201–212).

### 4.5 Techo combinado

| Modelo | Acierto (CV honesta) |
|---|:-:|
| Features absolutas | 35,3 % |
| **Features relativas (definitivo)** | **43,7 %** |

Juntar las 23 señales con ML **no mejora** la regla simple. Hemos tocado techo.

### 4.6 Estrategias prácticas

| Estrategia | Acierto |
|---|:-:|
| Azar puro | 25 % |
| Siempre «b» | 32 % |
| La opción más larga | 39 % |
| **La más larga sin «siempre/nunca/solo»** | **43 %** |

> 🏆 **Regla de oro:** ante la duda, elige la opción **más larga y detallada** (enumera con «y»,
> más comas), **descarta** las que digan «siempre/nunca/solo/todos» y **evita la «d»**.

---

## 5. Discusión

¿Por qué falla el texto y "leakean" las opciones? Porque **escribir 300 enunciados con sesgo de
posición de respuesta requiere intención**, mientras que **redactar la opción correcta con más
cuidado que los distractores es un sesgo inconsciente** difícil de evitar. La teoría de la
información lo cierra: 300 respuestas con esta marginal contienen ~585 bits de entropía; ninguna
codificación (conjunto de reglas) puede bajar de ahí en datos sin estructura real. La métrica
"nº de items a memorizar" es engañable porque cuenta una regla como 1 cosa aunque esconda muchos
bits; por eso solo comprime de verdad una regla con **disparador simple + cobertura alta**, que
únicamente existe si hay sesgo real — y aquí solo lo hay en las opciones, no en el enunciado.

---

## 6. La aplicación de estudio (`docs/`)

Web estática (Bootstrap 5, sin build, lista para GitHub Pages):

- **📖 Estudiar** — navega las 300, responde con feedback inmediato; filtros por tema y
  **⚠️ Trampas** (las 171 preguntas donde la heurística falla, a memorizar sí o sí).
- **📝 Examen** — simulacro aleatorio con nota final.
- **💡 Recursos** — todas las heurísticas con sus cifras reales.

Cada pregunta se **etiqueta** con sus patrones (negativa, meta-opción, ¿Cuál…?) y, tras responder,
con si la heurística acertó o falló.

---

## 7. Limitaciones

- ⚠️ **Las respuestas son orientativas** (kaixo.com / foros), **no oficiales**; pueden contener
  errores puntuales.
- Los porcentajes describen **este corpus concreto**; no son garantía sobre un examen distinto.
- Es una **ayuda de estudio**, no un sustituto de estudiar.

---

## 8. Reproducibilidad

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python parse_pdf.py          # qa.pdf  -> qa.json
python harvest_key.py        # (opcional) reconstruye key.json desde la web
python analyze.py real       # minado de reglas + Monte Carlo
python focused.py            # hipótesis dirigidas
python signals.py            # 23 señales + análisis de secuencia
python combined2.py          # techo combinado (CV honesta)
python tip_logic.py          # valida la lógica del tip (prior × longitud + gate)
python build_site_data.py    # genera docs/data.js para la web
```

Previsualizar la web: `cd docs && python -m http.server 8000`.

---

## 9. Estructura del repositorio

```
opos/
├── qa.pdf                 # enunciados (fuente)
├── parse_pdf.py           # PDF -> qa.json
├── harvest_key.py         # extrae key.json (respuestas)
├── features.py            # features del enunciado y selectores
├── analyze.py             # minado de reglas + Bonferroni + Monte Carlo
├── eda.py                 # análisis exploratorio
├── focused.py             # hipótesis pre-registradas
├── signals.py             # señales entre opciones + secuencia
├── combined.py/combined2.py  # modelo ML (CV honesta)
├── tip_logic.py           # validación de la lógica del tip por-pregunta
├── build_site_data.py     # genera los datos de la web
├── qa.json / key.json     # datos generados
└── docs/                  # web estática (GitHub Pages)
    ├── index.html
    ├── css/style.css
    ├── js/app.js
    └── data.js
```

---

## Aviso

Proyecto educativo y de análisis de datos. Las preguntas pertenecen a sus autores (Osakidetza); las
respuestas provienen de fuentes comunitarias orientativas. Úsese como apoyo al estudio.
