/* OPE Osakidetza 2026 — app estática (Bootstrap 5). Datos en window.QA / QA_META */
(function () {
  "use strict";
  const QA = window.QA, META = window.QA_META;
  const LETTERS = ["a", "b", "c", "d"];
  const byNum = Object.fromEntries(QA.map(q => [q.num, q]));
  const $ = s => document.querySelector(s);
  const $$ = s => document.querySelectorAll(s);
  const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
  const esc = s => s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const mainEl = document.querySelector("main");
  const scrollMainTop = () => { try { mainEl.scrollTo({ top: 0 }); } catch (e) { mainEl.scrollTop = 0; } };

  /* ---------- progreso ---------- */
  const PKEY = "opos_progress_v1";
  let progress = {};
  try { progress = JSON.parse(localStorage.getItem(PKEY)) || {}; } catch (e) {}
  const save = () => { try { localStorage.setItem(PKEY, JSON.stringify(progress)); } catch (e) {} };
  function record(num, ans, ok) { progress[num] = { ans, ok }; save(); updateTopProgress(); renderMenuStats(); }
  function updateTopProgress() {
    $("#progressLine").firstElementChild.style.width = (100 * Object.keys(progress).length / QA.length) + "%";
  }

  /* ---------- chip: solo temática ---------- */
  function preChips(q) { return `<span class="chip tema">${esc(q.tema)}</span>`; }

  /* ---------- tip por-pregunta (modal, analiza ESTA pregunta) ---------- */
  const U = s => s.toUpperCase();
  function tipHtml(q) {
    const b = [];
    if (q.longest) b.push(`La opción más larga es la <b>${U(q.longest)}</b> — la correcta suele ser la más extensa.`);
    if (q.optY && q.optY.length === 1) b.push(`Solo la opción <b>${U(q.optY[0])}</b> enumera con «y» (señal fuerte de correcta).`);
    if (q.comas) b.push(`La opción <b>${U(q.comas)}</b> es la más detallada (más comas).`);
    if (q.absLetters && q.absLetters.length) b.push(`Ojo: ${q.absLetters.map(U).join(", ")} usan «siempre/nunca/solo» → los absolutos suelen ser falsos, descártalos.`);
    if (q.meta) b.push(`La opción <b>${U(q.meta)}</b> es del tipo «todo/ninguna de las anteriores».`);
    if (q.cual) b.push(`Es una pregunta «¿Cuál…?»: en este examen tienden a la <b>C</b>.`);
    if (!b.length) b.push(`Sin señales claras en esta pregunta.`);
    return `<ul>${b.map(x => `<li>${x}</li>`).join("")}</ul>
            <div class="tip-suggest">👉 Ante la duda, marca la <b>${U(q.heurPred)}</b>.</div>`;
  }
  const tipModal = $("#tipModal");
  function openTip(q) { $("#tipBody").innerHTML = tipHtml(q); tipModal.classList.remove("d-none"); }
  function closeTip() { tipModal.classList.add("d-none"); }
  $("#tipClose").onclick = closeTip;
  tipModal.addEventListener("click", e => { if (e.target === tipModal) closeTip(); });

  /* ---------- tarjeta reutilizable ---------- */
  function renderCard(q, opts) {
    opts = opts || {};
    const card = el("div", "q-card");
    card.innerHTML =
      `<div class="chips">${preChips(q)}</div>
       <div class="qnum">Pregunta ${q.num}</div>
       <div class="qtext">${esc(q.pregunta)}</div>`;

    const hintBtn = el("button", "hint-btn", "💡 Ante la duda");
    hintBtn.onclick = () => openTip(q);
    card.appendChild(hintBtn);

    const optEls = {};
    LETTERS.forEach(L => {
      if (!q.opciones[L]) return;
      const o = el("button", "opt", `<span class="let">${L.toUpperCase()}</span><span>${esc(q.opciones[L])}</span>`);
      o.onclick = () => choose(L);
      optEls[L] = o; card.appendChild(o);
    });
    const fbSlot = el("div"); card.appendChild(fbSlot);

    let locked = false;
    function reveal(picked) {
      locked = true;
      hintBtn.classList.add("d-none");
      LETTERS.forEach(L => {
        const o = optEls[L]; if (!o) return;
        o.classList.add("disabled");
        if (L === q.correcta) o.classList.add("correct");
        else if (L === picked) o.classList.add("wrong");
        else o.classList.add("dim");
        o.onclick = null;
      });
      const ok = picked === q.correcta;
      fbSlot.appendChild(el("div", "feedback " + (ok ? "good" : "bad"),
        ok ? `<b>¡Correcta!</b> Era la <b>${q.correcta.toUpperCase()}</b>.`
           : `<b>Incorrecta.</b> La correcta es la <b>${q.correcta.toUpperCase()}</b>.`));
    }
    function choose(L) {
      if (locked) return;
      reveal(L);
      record(q.num, L, L === q.correcta);
      if (opts.onAnswer) opts.onAnswer(L === q.correcta, L);
    }
    return card;
  }

  /* ===================== ESTUDIAR ===================== */
  let studyList = [], studyIdx = 0;
  function buildThemeFilter() {
    const themes = Object.keys(META.themes).sort((a, b) => META.themes[b] - META.themes[a]);
    $("#themeFilter").innerHTML = `<option value="">Todos los temas (${QA.length})</option>` +
      themes.map(t => `<option value="${t}">${t} (${META.themes[t]})</option>`).join("");
  }
  function applyFilters() {
    const theme = $("#themeFilter").value;
    studyList = QA.filter(q => !theme || q.tema === theme);
    if (!studyList.length) studyList = QA.slice();
    studyIdx = 0;
    $("#qTotal").textContent = studyList.length;
    $("#jumpInput").max = studyList.length;
    renderStudy();
  }
  function renderStudy() {                 // SIEMPRE fresca: no revela respuesta previa
    const q = studyList[studyIdx];
    $("#jumpInput").value = studyIdx + 1;
    const slot = $("#studyCard"); slot.innerHTML = "";
    slot.appendChild(renderCard(q, {}));
    scrollMainTop();
  }
  function go(delta) { studyIdx = (studyIdx + delta + studyList.length) % studyList.length; renderStudy(); }
  $("#prevBtn").onclick = () => go(-1);
  $("#nextBtn").onclick = () => go(1);
  $("#jumpInput").onchange = () => {
    let v = parseInt($("#jumpInput").value, 10);
    if (isNaN(v)) v = 1; v = Math.max(1, Math.min(studyList.length, v));
    studyIdx = v - 1; renderStudy();
  };
  $("#themeFilter").onchange = applyFilters;

  /* ===================== EXAMEN ===================== */
  let exam = null;
  const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  function showExamNav(on) { $("#examNav").classList.toggle("d-none", !on); }
  $("#startExam").onclick = () => {
    const n = Math.min(parseInt($("#examLen").value, 10), QA.length);
    exam = { list: shuffle(QA.slice()).slice(0, n), idx: 0, right: 0, wrong: 0, answers: [] };
    $("#examSetup").classList.add("d-none"); $("#examResult").classList.add("d-none");
    $("#examRun").classList.remove("d-none"); $("#exTotal").textContent = n;
    $("#bottomNav").classList.add("d-none"); showExamNav(true);
    renderExam();
  };
  $("#quitExam").onclick = () => { exam = null; showExamNav(false); $("#examRun").classList.add("d-none"); $("#examSetup").classList.remove("d-none"); };
  function renderExam() {
    const q = exam.list[exam.idx];
    $("#exPos").textContent = exam.idx + 1;
    $("#exRight").textContent = exam.right; $("#exWrong").textContent = exam.wrong;
    $("#examBar").style.width = (100 * exam.idx / exam.list.length) + "%";
    const slot = $("#examCard"); slot.innerHTML = "";
    $("#examNext").disabled = true;                       // se habilita al responder
    slot.appendChild(renderCard(q, {
      onAnswer: ok => {
        exam.answers.push({ num: q.num, ok }); if (ok) exam.right++; else exam.wrong++;
        $("#exRight").textContent = exam.right; $("#exWrong").textContent = exam.wrong;
        $("#examNext").disabled = false;                  // siempre se corrige; habilita Siguiente
      }
    }));
    scrollMainTop();
  }
  $("#examNext").onclick = advance;
  function advance() { exam.idx++; if (exam.idx >= exam.list.length) finish(); else renderExam(); }
  function finish() {
    showExamNav(false);
    $("#examRun").classList.add("d-none");
    const total = exam.list.length, right = exam.right, pct = Math.round(100 * right / total);
    const wrongs = exam.answers.filter(a => !a.ok);
    let html = `<div class="result-card"><div class="result-big">${pct}%</div>
       <div class="text-secondary mb-3">${right} de ${total} correctas</div>
       <button class="btn btn-primary btn-lg w-100 fw-bold" id="againExam">Otro examen</button></div>`;
    if (wrongs.length) {
      html += `<div class="res-card mt-3"><h3 class="h6 fw-bold">Repasa los fallos (${wrongs.length})</h3>`;
      wrongs.forEach(w => { const q = byNum[w.num];
        html += `<div class="review-item"><b>#${q.num}</b><span>${esc(q.pregunta.slice(0, 90))}…
          <br><span class="text-secondary">Correcta <b>${q.correcta.toUpperCase()}</b>: ${esc(q.opciones[q.correcta].slice(0, 80))}</span></span></div>`; });
      html += `</div>`;
    }
    const res = $("#examResult"); res.classList.remove("d-none"); res.innerHTML = html;
    $("#againExam").onclick = () => { res.classList.add("d-none"); $("#examSetup").classList.remove("d-none"); };
  }

  /* ===================== RECURSOS ===================== */
  function renderResources() {
    const s = META.stats, m = META.marginal, n = META.n;
    $("#resContent").innerHTML = `
      <div class="res-card golden">
        <h3 class="h5 fw-bold">🏆 La regla de oro ante la duda</h3>
        <p class="mb-2">Si no te sabes la pregunta, elige la opción <b>más larga y detallada</b>
        (enumera con «y», más comas y matices) y <b>descarta</b> las que digan
        <b>«siempre / nunca / solo / todos»</b>. Evita la <b>«d»</b> salvo seguridad.</p>
        <div class="stat-grid">
          <div class="stat"><span class="big">${s.masLargaSinAbs}%</span><small>acierto con la regla</small></div>
          <div class="stat"><span class="big">${s.azar}%</span><small>azar puro</small></div>
        </div>
      </div>
      <div class="res-card">
        <h3 class="h6 fw-bold">📊 Señales encontradas (datos reales)</h3>
        <p class="text-secondary small">Sesgos medidos sobre las 300 respuestas. Todos apuntan a lo mismo:
        la correcta suele ser la <b>más larga, completa y matizada</b>.</p>
        <table class="strat">
          <tr><td>La opción que contiene «y» (enumera)</td><td>${s.tieneY}%</td></tr>
          <tr><td>La opción con más comas</td><td>${s.masComas}%</td></tr>
          <tr><td>La opción más larga</td><td>${s.masLarga}%</td></tr>
          <tr><td>Opciones con «siempre/nunca/solo» → correctas solo</td><td>${s.absolutaCorrecta}%</td></tr>
          <tr><td>Techo combinando todo (modelo ML validado)</td><td>${s.techoML}%</td></tr>
        </table>
      </div>
      <div class="res-card">
        <h3 class="h6 fw-bold">🎯 Sesgo de las letras</h3>
        <p class="text-secondary small">La distribución de respuestas NO es uniforme:</p>
        <div class="stat-grid">
          ${LETTERS.map(L => `<div class="stat"><span class="big">${Math.round(100*m[L]/n)}%</span><small>opción ${L.toUpperCase()} (${m[L]})</small></div>`).join("")}
        </div>
        <p class="note">«b»+«c» suman el ${Math.round(100*(m.b+m.c)/n)}%. La «d» es la más rara. Si dudas entre dos, antes b/c que d.</p>
      </div>
      <div class="res-card">
        <h3 class="h6 fw-bold">🧠 Cómo estudiar con esta web</h3>
        <ul class="ps-3 mb-0">
          <li class="my-2"><b>Estudiar:</b> navega las 300, responde y aprende los patrones. Filtra por tema.</li>
          <li class="my-2"><b>💡 Ante la duda:</b> en cada pregunta abre el tip para ver el análisis de sus opciones y la sugerencia.</li>
          <li class="my-2"><b>Examen:</b> simulacro aleatorio con nota final.</li>
          <li class="my-2">Tu progreso se guarda en el móvil.</li>
        </ul>
      </div>
      <div class="res-card">
        <h3 class="h6 fw-bold">🔬 ¿De dónde salen estos tips?</h3>
        <p class="text-secondary small mb-2">Del análisis de las 300 preguntas con control estadístico
        (Bonferroni, Monte Carlo, validación cruzada). Clave: el <b>texto de la pregunta NO predice</b> la
        respuesta; el único sesgo real está en <b>cómo se redactan las opciones</b>.</p>
        <p class="note">⚠️ Respuestas de origen orientativo (kaixo.com / foros), no oficiales.</p>
      </div>`;
  }

  /* ===================== NAVEGACIÓN ENTRE MODOS ===================== */
  const views = { study: "#view-study", exam: "#view-exam", res: "#view-res" };
  function switchView(v) {
    $$(".menu-item").forEach(m => m.classList.toggle("active", m.dataset.view === v));
    Object.entries(views).forEach(([k, sel]) => $(sel).classList.toggle("d-none", k !== v));
    $("#filterBar").classList.toggle("d-none", v !== "study");
    $("#bottomNav").classList.toggle("d-none", v !== "study");
    showExamNav(false);
    closeTip();
    if (v === "exam") {                 // reinicia el examen a la pantalla de configuración
      exam = null;
      $("#examRun").classList.add("d-none"); $("#examResult").classList.add("d-none");
      $("#examSetup").classList.remove("d-none");
    }
    if (v === "res") renderResources();
    scrollMainTop();
  }
  $$(".menu-item").forEach(m => m.addEventListener("click", () => switchView(m.dataset.view)));

  /* ---------- stats en el menú ---------- */
  function renderMenuStats() {
    const done = Object.keys(progress).length;
    const right = Object.values(progress).filter(p => p.ok).length;
    const pct = done ? Math.round(100 * right / done) : 0;
    $("#menuStats").innerHTML =
      `<div class="stat-row"><span>Respondidas</span><b>${done} / ${QA.length}</b></div>
       <div class="stat-row"><span>Aciertos</span><b>${right}</b></div>
       <div class="stat-row"><span>% acierto</span><b>${pct}%</b></div>`;
  }
  $("#resetProgress").onclick = () => {
    if (confirm("¿Borrar todo tu progreso?")) { progress = {}; save(); updateTopProgress(); renderMenuStats(); applyFilters(); }
  };

  /* ---------- init ---------- */
  buildThemeFilter();
  applyFilters();
  updateTopProgress();
  renderMenuStats();
  switchView("study");
})();
