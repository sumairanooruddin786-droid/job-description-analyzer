(() => {
  "use strict";

  const MAX_CHARS = 15000;
  const SAMPLE = `ABC Technologies is hiring an AI Engineer to join our growing product team (Full-time, Hybrid - Karachi).

Requirements:
- 2-4 years of professional experience building AI-powered applications
- Strong Python programming skills
- Experience with FastAPI for building REST APIs
- Hands-on experience with LangGraph or similar agent / workflow frameworks
- Good knowledge of SQL and relational databases
- Experience integrating LLM APIs such as Gemini or Groq is a plus

Responsibilities:
- Design and ship LLM workflows that transform raw text into structured data
- Collaborate with frontend engineers and product managers
- Write clean, modular and well-tested code
- Communicate progress clearly and solve problems independently in a fast-paced team`;

  const $ = (id) => document.getElementById(id);
  const input = $("jdInput"), counter = $("counter"), analyzeBtn = $("analyzeBtn");
  const errorBox = $("errorBox"), pipeline = $("pipeline");
  let lastReport = null;
  let timer = null;

  /* ---------- theme ---------- */
  const root = document.documentElement;
  const saved = (() => { try { return localStorage.getItem("theme"); } catch { return null; } })();
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = saved || (prefersDark ? "dark" : "light");
  $("themeToggle").addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch { /* ignore */ }
  });

  /* ---------- helpers ---------- */
  const updateCounter = () => {
    const n = input.value.length;
    counter.textContent = `${n.toLocaleString()} / ${MAX_CHARS.toLocaleString()}`;
    counter.style.color = n > MAX_CHARS ? "var(--danger)" : "";
  };
  const showError = (msg) => { errorBox.textContent = msg; errorBox.hidden = false; };
  const clearError = () => { errorBox.hidden = true; errorBox.textContent = ""; };
  const toast = (msg) => {
    const t = $("toast"); t.textContent = msg; t.hidden = false;
    setTimeout(() => { t.hidden = true; }, 1800);
  };
  const steps = () => [...pipeline.querySelectorAll("li")];
  const resetPipeline = () => steps().forEach((li) => { li.className = ""; li.querySelector("em").textContent = ""; });

  function renderTags(containerId, items, cls = "") {
    const el = $(containerId);
    el.className = `tags ${cls}`.trim();
    el.replaceChildren();
    if (!items || !items.length) {
      const s = document.createElement("span"); s.className = "none"; s.textContent = "Not specified"; el.append(s); return;
    }
    items.forEach((t) => { const s = document.createElement("span"); s.className = "tag"; s.textContent = t; el.append(s); });
  }

  /* Animate pipeline while the single API request is running */
  function startProgress() {
    resetPipeline();
    let i = 0;
    const list = steps();
    list[0].classList.add("active");
    timer = setInterval(() => {
      if (i < list.length - 1) {
        list[i].classList.replace("active", "done");
        i += 1; list[i].classList.add("active");
      }
    }, 1500);
  }
  function stopProgress(success, traces = []) {
    clearInterval(timer);
    const list = steps();
    if (success) {
      list.forEach((li, idx) => {
        li.className = "done";
        const t = traces[idx];
        li.querySelector("em").textContent = t ? `${(t.duration_ms / 1000).toFixed(1)}s` : "";
      });
    } else {
      list.forEach((li) => li.classList.remove("active"));
    }
  }

  /* ---------- render ---------- */
  function renderReport(data) {
    const r = data.report;
    lastReport = r;
    $("rTitle").textContent = r.job_title;
    $("rCompany").textContent = r.company;
    $("rExp").textContent = r.experience;
    $("rCat").textContent = r.job_category;
    $("rEmp").textContent = r.employment_type;
    $("rMode").textContent = r.work_mode;

    const top = $("rTop"); top.replaceChildren();
    r.top_3_skills.forEach((s, idx) => {
      const li = document.createElement("li");
      const rank = document.createElement("span"); rank.className = "rank"; rank.textContent = idx + 1;
      const name = document.createElement("span"); name.textContent = s;
      li.append(rank, name); top.append(li);
    });

    renderTags("rReq", r.required_skills);
    renderTags("rTech", r.technical_skills, "tech");
    renderTags("rSoft", r.soft_skills, "soft");
    $("rSummary").textContent = r.summary;
    $("rIdeal").textContent = r.ideal_candidate;
    const focus = $("rFocus"); focus.replaceChildren();
    r.interview_focus.forEach((f) => { const li = document.createElement("li"); li.textContent = f; focus.append(li); });
    $("meta").textContent = `Model: ${data.model} · Total time: ${(data.total_ms / 1000).toFixed(1)}s`;

    $("placeholder").hidden = true;
    $("report").hidden = false;
    $("report").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ---------- actions ---------- */
  async function analyze() {
    clearError();
    const text = input.value.trim();
    if (!text) return showError("Please paste a job description first.");
    if (text.length < 40) return showError("The job description is too short. Please paste the full posting.");
    if (text.length > MAX_CHARS) return showError(`The job description is too long (max ${MAX_CHARS.toLocaleString()} characters).`);

    analyzeBtn.disabled = true;
    analyzeBtn.querySelector(".btn-label").textContent = "Analyzing…";
    analyzeBtn.querySelector(".spinner").hidden = false;
    startProgress();

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: text }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.";
        throw new Error(detail);
      }
      stopProgress(true, data.steps);
      renderReport(data);
    } catch (err) {
      stopProgress(false);
      const offline = err instanceof TypeError;
      showError(offline ? "Cannot reach the server. Make sure the backend is running." : err.message);
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.querySelector(".btn-label").textContent = "Analyze";
      analyzeBtn.querySelector(".spinner").hidden = true;
    }
  }

  function exportJson() {
    if (!lastReport) return;
    const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const slug = lastReport.job_title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "report";
    a.href = url; a.download = `hiring-report-${slug}.json`;
    document.body.append(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    toast("JSON exported");
  }

  async function copyJson() {
    if (!lastReport) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(lastReport, null, 2));
      toast("JSON copied");
    } catch { toast("Copy failed"); }
  }

  analyzeBtn.addEventListener("click", analyze);
  $("exportBtn").addEventListener("click", exportJson);
  $("copyBtn").addEventListener("click", copyJson);
  $("sampleBtn").addEventListener("click", () => { input.value = SAMPLE; updateCounter(); clearError(); });
  $("clearBtn").addEventListener("click", () => {
    input.value = ""; updateCounter(); clearError(); resetPipeline();
    $("report").hidden = true; $("placeholder").hidden = false; lastReport = null;
  });
  input.addEventListener("input", updateCounter);
  input.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") analyze(); });
  updateCounter();
})();
