from __future__ import annotations


def render_index_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Python-YTRipper Web UI</title>
  <style>
    :root {
      --bg: #f6f1e8;
      --panel: #fffaf2;
      --ink: #20201c;
      --muted: #6d675e;
      --accent: #0e6b50;
      --accent-soft: #d7efe7;
      --border: #d5ccbd;
    }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, #f3dcc4 0, transparent 32%),
        linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
    }
    main {
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      gap: 18px;
    }
    .hero, .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 8px 30px rgba(32, 32, 28, 0.06);
    }
    .hero {
      padding: 24px;
    }
    .hero h1 {
      margin: 0 0 8px;
      font-size: 2rem;
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      max-width: 62ch;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 18px;
      min-width: 0;
    }
    .health-grid {
      display: grid;
      gap: 18px;
    }
    .control-grid {
      display: grid;
      grid-template-columns: minmax(280px, 0.9fr) minmax(420px, 1.35fr);
      gap: 18px;
      align-items: start;
      min-width: 0;
    }
    .workspace-grid {
      display: grid;
      grid-template-columns: minmax(280px, 0.95fr) minmax(320px, 1.05fr);
      gap: 18px;
      align-items: start;
      min-width: 0;
    }
    .panel {
      padding: 18px;
      min-width: 0;
      overflow: hidden;
    }
    .panel h2 {
      margin-top: 0;
      font-size: 1.1rem;
    }
    label {
      display: block;
      font-size: 0.92rem;
      margin-bottom: 6px;
    }
    input, select, button, textarea {
      width: 100%;
      box-sizing: border-box;
      border-radius: 10px;
      border: 1px solid var(--border);
      padding: 10px 12px;
      font: inherit;
      background: #fffdf9;
    }
    textarea {
      min-height: 130px;
      resize: vertical;
    }
    button {
      cursor: pointer;
      background: var(--accent);
      color: white;
      border: none;
    }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.65;
    }
    button.secondary {
      background: var(--accent-soft);
      color: var(--ink);
      border: 1px solid #badfd1;
    }
    .stack {
      display: grid;
      gap: 12px;
    }
    .row {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    }
    .toggles-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      align-items: start;
    }
    .field-grid {
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      align-items: start;
    }
    .note {
      font-size: 0.88rem;
      color: var(--muted);
    }
    .status {
      white-space: pre-wrap;
      font-family: "Courier New", monospace;
      font-size: 0.9rem;
      background: #fcf8f1;
      border: 1px dashed var(--border);
      border-radius: 12px;
      padding: 12px;
      min-height: 160px;
      overflow: auto;
    }
    .jobs-list {
      display: grid;
      gap: 8px;
      max-height: 560px;
      overflow: auto;
      padding-right: 4px;
    }
    .job-card {
      border: 1px solid var(--border);
      background: #fcf8f1;
      border-radius: 12px;
      padding: 10px 12px;
      text-align: left;
      color: var(--ink);
    }
    .job-card.active {
      border-color: var(--accent);
      background: #eef8f4;
    }
    .job-card strong,
    .job-card span {
      display: block;
    }
    .job-card span {
      color: var(--muted);
      font-size: 0.88rem;
      margin-top: 2px;
    }
    .detail-grid {
      display: grid;
      gap: 10px;
      min-width: 0;
    }
    .detail-block {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: #fcf8f1;
      padding: 12px;
      min-width: 0;
    }
    .detail-block h3 {
      margin: 0 0 8px;
      font-size: 0.98rem;
    }
    .detail-list {
      margin: 0;
      padding-left: 18px;
      color: var(--ink);
    }
    .detail-list li {
      margin-bottom: 6px;
    }
    .detail-meta {
      margin-top: 4px;
      color: var(--muted);
      font-size: 0.86rem;
    }
    .health-list {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      align-items: start;
    }
    .health-item {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: #fcf8f1;
      padding: 12px;
      min-width: 0;
    }
    .health-item.ok {
      border-color: #badfd1;
      background: #eef8f4;
    }
    .health-item.fail {
      border-color: #dfbaba;
      background: #fbefef;
    }
    .health-item strong,
    .health-item span {
      display: block;
    }
    .health-item span {
      color: var(--muted);
      font-size: 0.88rem;
      margin-top: 4px;
    }
    .health-summary {
      font-size: 0.92rem;
      color: var(--muted);
    }
    .pill {
      display: inline-block;
      width: auto;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.86rem;
      border: 1px solid var(--border);
      background: #fcf8f1;
      color: var(--muted);
    }
    .pill.ok {
      border-color: #badfd1;
      background: #eef8f4;
      color: #184d3b;
    }
    .pill.warn {
      border-color: #d8c6a8;
      background: #fbf3df;
      color: #765c22;
    }
    .pill.fail {
      border-color: #dfbaba;
      background: #fbefef;
      color: #7a3030;
    }
    .action-banner {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: #fcf8f1;
      padding: 10px 12px;
      font-size: 0.9rem;
      color: var(--muted);
    }
    .action-banner.ok {
      border-color: #badfd1;
      background: #eef8f4;
      color: #184d3b;
    }
    .action-banner.fail {
      border-color: #dfbaba;
      background: #fbefef;
      color: #7a3030;
    }
    .inspector-shell {
      display: grid;
      gap: 10px;
    }
    .inspector-summary {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: #fcf8f1;
      padding: 12px;
      font-size: 0.92rem;
      min-width: 0;
    }
    .inspector-summary strong,
    .inspector-summary span {
      display: block;
    }
    .inspector-summary span {
      color: var(--muted);
      margin-top: 4px;
    }
    .raw-output {
      max-height: 560px;
      overflow: auto;
    }
    .field-note {
      margin-top: 5px;
      font-size: 0.82rem;
      color: var(--muted);
    }
    @media (max-width: 980px) {
      .control-grid,
      .workspace-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Python-YTRipper Web UI</h1>
      <p>
        This is the first working web shell for the downloader. It is intentionally simple:
        inspect a video or playlist URL, tweak session settings, start a job, and watch the job list grow.
      </p>
    </section>

    <section class="panel health-grid">
      <div>
        <h2>Health & Status</h2>
        <div id="health-summary" class="health-summary">Checking backend health...</div>
      </div>
      <div id="health-output" class="health-list">
        <div class="status">Checking backend health...</div>
      </div>
    </section>

    <section class="control-grid">
      <div class="panel stack">
        <h2>Download</h2>
        <label for="url">YouTube URL</label>
        <input id="url" placeholder="https://www.youtube.com/watch?v=..." />
        <div id="url-status" class="pill">Paste a video or playlist URL to validate it locally.</div>
        <div class="row">
          <button id="inspect-btn" class="secondary" type="button" disabled>Inspect URL</button>
          <button id="download-btn" type="button" disabled>Start Job</button>
        </div>
        <div id="action-output" class="action-banner">Ready. Start with a valid YouTube video or playlist URL.</div>
        <p class="note">The current UI supports one top-level video or playlist URL per job. Batch/file workflows can follow later.</p>
      </div>

      <div class="panel stack">
        <h2>Session Config</h2>
        <div class="toggles-grid">
          <label><input id="audio-only" type="checkbox" /> Audio only</label>
          <label><input id="audio-mp3" type="checkbox" /> Convert to MP3</label>
          <label><input id="autotag" type="checkbox" /> Autotag</label>
          <label><input id="save-results" type="checkbox" /> Save results</label>
          <label><input id="no-dir-date" type="checkbox" /> Do not prefix playlist folder with date</label>
        </div>
        <div class="field-grid">
          <div>
            <label for="download-dir">Download directory</label>
            <input id="download-dir" placeholder="~/Downloads/RipperDownloads" />
          </div>
          <div>
            <label for="preset-select">Load preset</label>
            <select id="preset-select"></select>
          </div>
          <div>
            <label for="quality-select">Quality</label>
            <select id="quality-select">
              <option value="">Best available</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div>
            <label for="resolution-select">Max resolution</label>
            <select id="resolution-select">
              <option value="">Best available</option>
              <option value="144p">144p</option>
              <option value="240p">240p</option>
              <option value="360p">360p</option>
              <option value="480p">480p</option>
              <option value="720p">720p</option>
              <option value="1080p">1080p</option>
              <option value="1440p">1440p</option>
              <option value="2160p">2160p</option>
            </select>
          </div>
          <div>
            <label for="abr-select">Audio bitrate</label>
            <select id="abr-select">
              <option value="">Best available</option>
              <option value="48k">48 kbps</option>
              <option value="50k">50 kbps</option>
              <option value="56k">56 kbps</option>
              <option value="64k">64 kbps</option>
              <option value="96k">96 kbps</option>
              <option value="128k">128 kbps</option>
              <option value="192k">192 kbps</option>
              <option value="256k">256 kbps</option>
              <option value="320k">320 kbps</option>
            </select>
          </div>
          <div>
            <label for="fps-select">Frame rate</label>
            <select id="fps-select">
              <option value="0">Any</option>
              <option value="30">Prefer 30 fps</option>
              <option value="60">Prefer 60 fps</option>
            </select>
            <div class="field-note">Applied only when video streams offer multiple frame-rate choices.</div>
          </div>
        </div>
        <div class="row">
          <button id="save-config-btn" class="secondary" type="button">Save Config</button>
          <button id="apply-session-btn" type="button">Apply Session Settings</button>
        </div>
      </div>
    </section>

    <section class="workspace-grid">
      <div class="panel stack">
        <h2>Inspector</h2>
        <div class="inspector-shell">
          <div id="inspect-summary" class="inspector-summary">
            <strong>No inspection yet.</strong>
            <span>Inspect a URL to see a readable summary here before opening the raw payload.</span>
          </div>
          <div id="inspect-output" class="status raw-output">No inspection yet.</div>
        </div>
      </div>
      <div class="panel stack">
        <h2>Jobs</h2>
        <div id="jobs-output" class="jobs-list">
          <div class="status">No jobs yet.</div>
        </div>
      </div>
    </section>

    <section class="panel stack">
      <h2>Job Detail</h2>
      <div id="job-detail-output" class="status">Select a job to inspect its items and events.</div>
      <div class="note">
        V1 note: this detail view is intentionally simple and summary-focused. It is here to make playlist and failed-job inspection useful before the larger next iteration.
      </div>
    </section>
  </main>

  <script>
    const urlInput = document.getElementById("url");
    const urlStatus = document.getElementById("url-status");
    const inspectButton = document.getElementById("inspect-btn");
    const downloadButton = document.getElementById("download-btn");
    const actionOutput = document.getElementById("action-output");
    const inspectSummary = document.getElementById("inspect-summary");
    const healthSummary = document.getElementById("health-summary");
    const healthOutput = document.getElementById("health-output");
    const inspectOutput = document.getElementById("inspect-output");
    const jobsOutput = document.getElementById("jobs-output");
    const jobDetailOutput = document.getElementById("job-detail-output");
    const presetSelect = document.getElementById("preset-select");
    let selectedJobId = "";
    let validationTimer = null;
    let currentUrlValidation = {
      url: "",
      valid: false,
      isPlaylist: false,
    };

    async function api(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Request failed: ${response.status}`);
      }
      return response.json();
    }

    function collectSessionUpdates() {
      const abrSelectValue = document.getElementById("abr-select").value;
      return {
        audio_only: document.getElementById("audio-only").checked,
        audio_mp3: document.getElementById("audio-mp3").checked,
        autotag: document.getElementById("autotag").checked,
        save_results: document.getElementById("save-results").checked,
        no_dir_date: document.getElementById("no-dir-date").checked,
        preferred_video_quality: document.getElementById("quality-select").value,
        preferred_audio_quality: document.getElementById("quality-select").value,
        preferred_resolution: document.getElementById("resolution-select").value,
        preferred_abr: abrSelectValue ? abrSelectValue.replace("kbps", "k") : "",
        preferred_fps: Number(document.getElementById("fps-select").value || 0),
        default_download_directory: document.getElementById("download-dir").value
      };
    }

    function applySessionState(state) {
      const options = state.options || {};
      document.getElementById("audio-only").checked = !!options.audio_only;
      document.getElementById("audio-mp3").checked = !!options.audio_mp3;
      document.getElementById("autotag").checked = !!options.autotag;
      document.getElementById("save-results").checked = !!options.save_results;
      document.getElementById("no-dir-date").checked = !!options.no_dir_date;
      document.getElementById("download-dir").value = options.default_download_directory || "";
      document.getElementById("quality-select").value = options.preferred_video_quality || "";
      document.getElementById("resolution-select").value = options.preferred_resolution || "";
      if (options.preferred_abr) {
        const normalizedAbr = String(options.preferred_abr);
        document.getElementById("abr-select").value = normalizedAbr.endsWith("kbps")
          ? normalizedAbr
          : `${normalizedAbr.replace(/k$/, "")}kbps`;
      } else {
        document.getElementById("abr-select").value = "";
      }
      document.getElementById("fps-select").value = String(options.preferred_fps || 0);
    }

    async function loadSessionState() {
      const state = await api("/api/session-config");
      applySessionState(state);
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    function formatHealthDetails(details) {
      const entries = Object.entries(details || {});
      if (!entries.length) {
        return "";
      }
      return entries
        .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : value}`)
        .join(" | ");
    }

    async function refreshHealth() {
      const payload = await api("/api/health");
      const items = payload.items || [];

      healthSummary.textContent = payload.ok
        ? `Backend ready. ${items.length} checks passed.`
        : `Backend needs attention. ${items.filter(item => item.ok).length}/${items.length} checks passed.`;

      healthOutput.innerHTML = items.map(item => {
        const itemClass = item.ok ? "ok" : "fail";
        const details = formatHealthDetails(item.details);
        return `
          <div class="health-item ${itemClass}">
            <strong>${item.ok ? "OK" : "Issue"} | ${escapeHtml(item.name || "")}</strong>
            <span>${escapeHtml(item.message || "")}</span>
            ${details ? `<span>${escapeHtml(details)}</span>` : ""}
          </div>
        `;
      }).join("");
    }

    function setActionMessage(message, tone = "") {
      actionOutput.className = tone ? `action-banner ${tone}` : "action-banner";
      actionOutput.textContent = message;
    }

    function renderInspectionSummary(payload) {
      const typeLabel = payload.is_playlist ? "Playlist" : "Video";
      const accessLabel = payload.remote_checked
        ? (payload.remotely_accessible ? "Reachable" : "Not reachable")
        : "Local-only check";
      const itemCountLabel = payload.item_count == null ? "Unknown" : String(payload.item_count);

      inspectSummary.innerHTML = `
        <strong>${escapeHtml(payload.title || "Inspection ready")}</strong>
        <span>${escapeHtml(typeLabel)} | ${escapeHtml(accessLabel)} | Items: ${escapeHtml(itemCountLabel)}</span>
        <span>${escapeHtml(payload.cleaned_url || payload.normalized_url || payload.url || "")}</span>
      `;
    }

    function updateUrlControls() {
      const hasUrl = !!urlInput.value.trim();
      const sameUrl = currentUrlValidation.url === urlInput.value.trim();
      const canUseUrl = hasUrl && sameUrl && currentUrlValidation.valid;
      inspectButton.disabled = !hasUrl;
      downloadButton.disabled = !canUseUrl;
    }

    function renderUrlValidation(result, pending = false) {
      if (pending) {
        urlStatus.className = "pill warn";
        urlStatus.textContent = "Checking URL format...";
        updateUrlControls();
        return;
      }

      if (!result.url) {
        urlStatus.className = "pill";
        urlStatus.textContent = "Paste a video or playlist URL to validate it locally.";
        updateUrlControls();
        return;
      }

      if (!result.looks_like_youtube_url) {
        urlStatus.className = "pill fail";
        urlStatus.textContent = "This does not look like a supported YouTube URL.";
        updateUrlControls();
        return;
      }

      urlStatus.className = "pill ok";
      urlStatus.textContent = result.is_playlist
        ? "Looks like a YouTube playlist URL."
        : "Looks like a YouTube video URL.";
      updateUrlControls();
    }

    async function validateUrlLocally() {
      const url = urlInput.value.trim();
      currentUrlValidation = {
        url,
        valid: false,
        isPlaylist: false,
      };

      if (!url) {
        renderUrlValidation({ url: "" });
        return;
      }

      renderUrlValidation({ url }, true);
      const result = await api("/api/url/inspect", {
        method: "POST",
        body: JSON.stringify({ url, remote_check: false, fetch_info: false })
      });

      if (urlInput.value.trim() !== url) {
        return;
      }

      currentUrlValidation = {
        url,
        valid: !!result.looks_like_youtube_url,
        isPlaylist: !!result.is_playlist,
      };
      renderUrlValidation(result);
    }

    async function loadPresets() {
      const presets = await api("/api/presets");
      presetSelect.innerHTML = "";
      for (const preset of presets) {
        const option = document.createElement("option");
        option.value = preset.id;
        option.textContent = `${preset.kind}: ${preset.label}`;
        presetSelect.appendChild(option);
      }
    }

    async function renderJobDetail(jobId) {
      selectedJobId = jobId;
      const detail = await api(`/api/jobs/${jobId}`);
      const summary = detail.summary || {};
      const items = detail.items || [];
      const events = detail.events || [];

      const itemMarkup = items.length
        ? `<ol class="detail-list">${items.map(item =>
            `<li>
              <strong>${item.success === true ? "OK" : item.success === false ? "Fail" : "Pending"} | ${escapeHtml(item.label || item.source_url || item.item_id)}</strong>
              <div class="detail-meta">Status: ${escapeHtml(item.status)}</div>
              ${item.output_path ? `<div class="detail-meta">Output: ${escapeHtml(item.output_path)}</div>` : ""}
              ${item.error ? `<div class="detail-meta">Error: ${escapeHtml(item.error)}</div>` : ""}
            </li>`
          ).join("")}</ol>`
        : '<p class="note">No item results recorded yet.</p>';

      const eventMarkup = events.length
        ? `<ol class="detail-list">${events.map(event =>
            `<li><strong>${escapeHtml(event.event_type)}</strong> - ${escapeHtml(event.message || "")}</li>`
          ).join("")}</ol>`
        : '<p class="note">No lifecycle events recorded yet.</p>';

      jobDetailOutput.className = "";
      jobDetailOutput.innerHTML = `
        <div class="detail-grid">
          <div class="detail-block">
            <h3>Summary</h3>
            <div><strong>Status:</strong> ${escapeHtml(summary.status || "")}</div>
            <div><strong>Kind:</strong> ${escapeHtml(summary.job_kind || "")}</div>
            <div><strong>Source:</strong> ${escapeHtml(summary.source_label || "")}</div>
            <div><strong>Items:</strong> ${escapeHtml(summary.items_done || 0)}/${escapeHtml(summary.items_total || 0)}</div>
            <div><strong>Failed:</strong> ${escapeHtml(summary.items_failed || 0)}</div>
            <div><strong>Current item:</strong> ${escapeHtml(summary.current_item_label || "")}</div>
            <div><strong>Download dir:</strong> ${escapeHtml(summary.download_dir || "")}</div>
            <div><strong>Playlist dir:</strong> ${escapeHtml(summary.playlist_dir || "")}</div>
            <div><strong>Results file:</strong> ${escapeHtml(summary.results_path || "")}</div>
          </div>
          <div class="detail-block">
            <h3>Items</h3>
            ${itemMarkup}
          </div>
          <div class="detail-block">
            <h3>Events</h3>
            ${eventMarkup}
          </div>
        </div>
      `;
    }

    async function refreshJobs() {
      const jobs = await api("/api/jobs");
      if (!jobs.length) {
        jobsOutput.innerHTML = '<div class="status">No jobs yet.</div>';
        jobDetailOutput.className = "status";
        jobDetailOutput.textContent = "Select a job to inspect its items and events.";
        selectedJobId = "";
        return;
      }

      jobsOutput.innerHTML = jobs.map(job => {
        const isActive = selectedJobId && selectedJobId === job.job_id ? " active" : "";
        return `
          <button class="job-card${isActive}" type="button" data-job-id="${escapeHtml(job.job_id)}">
            <strong>${escapeHtml(job.status)} | ${escapeHtml(job.job_kind)}</strong>
            <span>${escapeHtml(job.items_done || 0)}/${escapeHtml(job.items_total || 0)} complete</span>
            <span>${escapeHtml(job.source_label || "")}</span>
          </button>
        `;
      }).join("");

      for (const button of jobsOutput.querySelectorAll("[data-job-id]")) {
        button.addEventListener("click", async () => {
          const jobId = button.getAttribute("data-job-id");
          await renderJobDetail(jobId);
          await refreshJobs();
        });
      }

      if (!selectedJobId && jobs.length) {
        await renderJobDetail(jobs[0].job_id);
        await refreshJobs();
        return;
      }

      if (selectedJobId && jobs.some(job => job.job_id === selectedJobId)) {
        await renderJobDetail(selectedJobId);
      }
    }

    document.getElementById("apply-session-btn").addEventListener("click", async () => {
      const state = await api("/api/session-config", {
        method: "POST",
        body: JSON.stringify({ updates: collectSessionUpdates() })
      });
      applySessionState(state);
    });

    document.getElementById("save-config-btn").addEventListener("click", async () => {
      await api("/api/presets/save", {
        method: "POST",
        body: JSON.stringify({ save_config: "true" })
      });
    });

    presetSelect.addEventListener("change", async () => {
      const state = await api("/api/presets/load", {
        method: "POST",
        body: JSON.stringify({ preset_id: presetSelect.value })
      });
      applySessionState(state);
    });

    urlInput.addEventListener("input", () => {
      clearTimeout(validationTimer);
      updateUrlControls();
      validationTimer = setTimeout(() => {
        validateUrlLocally().catch(error => {
          renderUrlValidation({ url: urlInput.value.trim() });
          setActionMessage(`URL validation failed: ${String(error)}`, "fail");
        });
      }, 600);
    });

    inspectButton.addEventListener("click", async () => {
      const url = urlInput.value.trim();
      const payload = await api("/api/url/inspect", {
        method: "POST",
        body: JSON.stringify({ url, remote_check: true, fetch_info: true })
      });
      currentUrlValidation = {
        url,
        valid: !!payload.looks_like_youtube_url,
        isPlaylist: !!payload.is_playlist,
      };
      renderUrlValidation(payload);
      setActionMessage(
        payload.title
          ? `Inspection loaded: ${payload.title}`
          : "Inspection completed.",
        payload.error ? "fail" : "ok"
      );
      renderInspectionSummary(payload);
      inspectOutput.textContent = JSON.stringify(payload, null, 2);
    });

    downloadButton.addEventListener("click", async () => {
      const url = urlInput.value.trim();
      if (!currentUrlValidation.valid || currentUrlValidation.url !== url) {
        setActionMessage("Validate a supported YouTube URL before starting a job.", "fail");
        return;
      }
      const job = await api("/api/jobs/download", {
        method: "POST",
        body: JSON.stringify({ url })
      });
      selectedJobId = job.job_id;
      setActionMessage(
        `Started ${job.job_kind || "download"} job ${job.job_id} for ${job.source_label || url}.`,
        "ok"
      );
      await refreshJobs();
    });

    refreshHealth().catch(error => {
      healthSummary.textContent = "Backend health could not be loaded.";
      healthOutput.innerHTML = `<div class="status">${escapeHtml(String(error))}</div>`;
    });
    updateUrlControls();
    loadSessionState().catch(error => { inspectOutput.textContent = String(error); });
    loadPresets().catch(error => { inspectOutput.textContent = String(error); });
    refreshJobs().catch(error => { jobsOutput.textContent = String(error); });
    setInterval(() => refreshHealth().catch(() => {}), 10000);
    setInterval(() => refreshJobs().catch(() => {}), 2000);
  </script>
</body>
</html>
"""
