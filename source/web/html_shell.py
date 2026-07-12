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
      padding: clamp(14px, 2vw, 24px);
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
      min-width: 0;
    }
    .control-grid {
      display: grid;
      grid-template-columns: minmax(300px, 0.88fr) minmax(420px, 1.12fr);
      gap: 18px;
      align-items: start;
      min-width: 0;
    }
    .workspace-grid {
      display: grid;
      grid-template-columns: minmax(300px, 0.92fr) minmax(340px, 1.08fr);
      gap: 18px;
      align-items: stretch;
      min-width: 0;
    }
    .panel {
      padding: 18px;
      min-width: 0;
      overflow: hidden;
    }
    .workspace-panel {
      min-height: 620px;
      display: grid;
      grid-template-rows: auto 1fr;
      align-self: stretch;
    }
    .detail-panel {
      min-width: 0;
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
      min-height: 0;
      height: 100%;
      overflow: auto;
      padding-right: 4px;
      align-content: start;
    }
    .job-card {
      border: 1px solid var(--border);
      background: #fcf8f1;
      border-radius: 12px;
      padding: 10px 12px;
      text-align: left;
      color: var(--ink);
      min-width: 0;
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
    .job-card-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .job-card-title {
      font-weight: 700;
      text-align: left;
    }
    .job-card-subtitle {
      font-size: 0.86rem;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .job-card-metrics {
      display: grid;
      gap: 4px;
      margin-top: 8px;
    }
    .job-badge {
      display: inline-block;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 0.78rem;
      background: #efe7d8;
      color: var(--ink);
      white-space: nowrap;
    }
    .job-badge.completed,
    .job-badge.success {
      background: #dff2eb;
      color: #184d3b;
    }
    .job-badge.failed {
      background: #f6dddd;
      color: #7a3030;
    }
    .job-badge.partial,
    .job-badge.running,
    .job-badge.validating,
    .job-badge.queued {
      background: #f4ecd8;
      color: #765c22;
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
    .summary-list {
      display: grid;
      gap: 8px;
    }
    .summary-row {
      display: grid;
      grid-template-columns: minmax(130px, 170px) 1fr;
      gap: 10px;
      align-items: start;
    }
    .summary-row strong {
      display: block;
    }
    .summary-value {
      overflow-wrap: anywhere;
    }
    .summary-value.empty {
      color: var(--muted);
      font-style: italic;
    }
    .health-list {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr));
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
      overflow-wrap: anywhere;
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
    .field-note.ok {
      color: #184d3b;
    }
    .field-note.warn {
      color: #765c22;
    }
    .inspector-shell {
      display: grid;
      gap: 10px;
      min-height: 0;
      grid-template-rows: auto minmax(120px, 1fr) auto;
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
    .inspector-readable {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: #fcf8f1;
      padding: 12px;
      font-size: 0.9rem;
      min-height: 0;
      overflow: auto;
    }
    .inspector-readable ul {
      margin: 0;
      padding-left: 18px;
    }
    .inspector-readable li {
      margin-bottom: 6px;
    }
    .inspector-raw details {
      border: 1px dashed var(--border);
      border-radius: 12px;
      padding: 10px 12px;
      background: #fcf8f1;
      max-height: 300px;
      overflow: auto;
    }
    .inspector-raw summary {
      cursor: pointer;
      font-weight: 700;
    }
    .raw-output {
      max-height: 240px;
      overflow: auto;
    }
    .field-note {
      margin-top: 5px;
      font-size: 0.82rem;
      color: var(--muted);
    }
    #job-detail-output {
      min-height: 0;
      max-height: 720px;
      overflow: auto;
    }
    #job-detail-output .detail-grid {
      min-width: 0;
    }
    #job-detail-output .detail-block {
      overflow: hidden;
    }
    #job-detail-output .detail-list,
    #job-detail-output .summary-list,
    .health-item span,
    .health-summary,
    .job-card-subtitle {
      overflow-wrap: anywhere;
    }
    @media (max-width: 1240px) {
      .control-grid {
        grid-template-columns: minmax(280px, 0.9fr) minmax(320px, 1.1fr);
      }
      .workspace-grid {
        grid-template-columns: minmax(260px, 0.9fr) minmax(300px, 1.1fr);
      }
    }
    @media (max-width: 980px) {
      .control-grid,
      .workspace-grid {
        grid-template-columns: 1fr;
      }
      .workspace-panel {
        min-height: 0;
      }
      .jobs-list,
      #job-detail-output {
        max-height: none;
      }
    }
    @media (max-width: 760px) {
      .hero {
        padding: 18px;
      }
      .hero h1 {
        font-size: 1.55rem;
      }
      .row,
      .field-grid,
      .toggles-grid,
      .health-list {
        grid-template-columns: 1fr;
      }
      .summary-row {
        grid-template-columns: 1fr;
      }
      .job-card-head {
        flex-direction: column;
        align-items: flex-start;
      }
      .inspector-shell {
        grid-template-rows: auto minmax(100px, 1fr) auto;
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
        <div id="config-source-banner" class="action-banner">Loading config source...</div>
        <div id="config-sync-banner" class="action-banner">Checking save target state...</div>
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
        <div id="config-form-note" class="field-note">Loading session config...</div>
      </div>
    </section>

    <section class="workspace-grid">
      <div class="panel stack workspace-panel">
        <h2>Inspector</h2>
        <div class="inspector-shell">
          <div id="inspect-summary" class="inspector-summary">
            <strong>No inspection yet.</strong>
            <span>Inspect a URL to see a readable summary here before opening the raw payload.</span>
          </div>
          <div id="inspect-readable" class="inspector-readable">No inspection yet.</div>
          <div class="inspector-raw">
            <details>
              <summary>Raw inspection payload</summary>
              <div id="inspect-output" class="status raw-output">No inspection yet.</div>
            </details>
          </div>
        </div>
      </div>
      <div class="panel stack workspace-panel">
        <h2>Jobs</h2>
        <div id="jobs-output" class="jobs-list">
          <div class="status">No jobs yet.</div>
        </div>
      </div>
    </section>

    <section class="panel stack detail-panel">
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
    const inspectReadable = document.getElementById("inspect-readable");
    const healthSummary = document.getElementById("health-summary");
    const healthOutput = document.getElementById("health-output");
    const inspectOutput = document.getElementById("inspect-output");
    const jobsOutput = document.getElementById("jobs-output");
    const jobDetailOutput = document.getElementById("job-detail-output");
    const presetSelect = document.getElementById("preset-select");
    const configSourceBanner = document.getElementById("config-source-banner");
    const configSyncBanner = document.getElementById("config-sync-banner");
    const configFormNote = document.getElementById("config-form-note");
    const applySessionButton = document.getElementById("apply-session-btn");
    const saveConfigButton = document.getElementById("save-config-btn");
    const sessionFieldIds = [
      "audio-only",
      "audio-mp3",
      "autotag",
      "save-results",
      "no-dir-date",
      "download-dir",
      "quality-select",
      "resolution-select",
      "abr-select",
      "fps-select",
    ];
    let selectedJobId = "";
    let validationTimer = null;
    let currentSessionState = null;
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

    function normalizeAbrSelectValue(value) {
      const normalized = String(value || "").trim();
      if (!normalized) {
        return "";
      }
      return normalized.endsWith("kbps")
        ? `${normalized.replace(/kbps$/, "")}k`
        : normalized;
    }

    function sessionUpdatesFromOptions(options = {}) {
      const qualityValue = options.preferred_video_quality || options.preferred_audio_quality || "";
      return {
        audio_only: !!options.audio_only,
        audio_mp3: !!options.audio_mp3,
        autotag: !!options.autotag,
        save_results: !!options.save_results,
        no_dir_date: !!options.no_dir_date,
        preferred_video_quality: qualityValue,
        preferred_audio_quality: qualityValue,
        preferred_resolution: options.preferred_resolution || "",
        preferred_abr: normalizeAbrSelectValue(options.preferred_abr || ""),
        preferred_fps: Number(options.preferred_fps || 0),
        default_download_directory: options.default_download_directory || ""
      };
    }

    function setBanner(element, message, tone = "") {
      element.className = tone ? `action-banner ${tone}` : "action-banner";
      element.textContent = message;
    }

    function syncPresetSelection() {
      if (!currentSessionState) {
        return;
      }
      const loadedId = currentSessionState.preset_details?.loaded_id || "default";
      presetSelect.value = loadedId;
    }

    function refreshConfigFormState() {
      if (!currentSessionState) {
        configFormNote.className = "field-note";
        configFormNote.textContent = "Loading session config...";
        applySessionButton.disabled = true;
        return;
      }

      const formSnapshot = JSON.stringify(collectSessionUpdates());
      const sessionSnapshot = JSON.stringify(sessionUpdatesFromOptions(currentSessionState.options || {}));
      const hasLocalChanges = formSnapshot !== sessionSnapshot;

      configFormNote.className = hasLocalChanges ? "field-note warn" : "field-note ok";
      configFormNote.textContent = hasLocalChanges
        ? "Local form changes are waiting to be applied to this session."
        : "Form matches the current in-memory session settings.";
      applySessionButton.disabled = !hasLocalChanges;
    }

    function renderConfigState(state) {
      const presetDetails = state.preset_details || {};
      const configSync = state.config_sync || {};
      const loadedLabel = presetDetails.loaded_label || "Default profile";
      const loadedKind = presetDetails.loaded_kind || "default";
      const saveTargetLabel = presetDetails.save_target_label || "Default profile";
      const sourceMessage = loadedKind === "immutable"
        ? `Loaded source: ${loadedLabel} preset. Save Config will not overwrite immutable presets.`
        : `Loaded source: ${loadedLabel}.`;
      const saveTone = configSync.has_unsaved_changes ? "warn" : "ok";
      const savePath = presetDetails.save_target_path || "";

      setBanner(configSourceBanner, sourceMessage, "ok");
      setBanner(
        configSyncBanner,
        `${configSync.status_label || `Save Config writes to ${saveTargetLabel}.`}${savePath ? ` Target: ${savePath}` : ""}`,
        saveTone
      );
      saveConfigButton.disabled = false;
      syncPresetSelection();
      refreshConfigFormState();
    }

    function applySessionState(state) {
      currentSessionState = state;
      const options = state.options || {};
      document.getElementById("audio-only").checked = !!options.audio_only;
      document.getElementById("audio-mp3").checked = !!options.audio_mp3;
      document.getElementById("autotag").checked = !!options.autotag;
      document.getElementById("save-results").checked = !!options.save_results;
      document.getElementById("no-dir-date").checked = !!options.no_dir_date;
      document.getElementById("download-dir").value = options.default_download_directory || "";
      document.getElementById("quality-select").value = options.preferred_video_quality || options.preferred_audio_quality || "";
      document.getElementById("resolution-select").value = options.preferred_resolution || "";
      document.getElementById("abr-select").value = normalizeAbrSelectValue(options.preferred_abr || "");
      document.getElementById("fps-select").value = String(options.preferred_fps || 0);
      renderConfigState(state);
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

    function formatPathValue(value, fallback = "Not recorded for this job.") {
      return value
        ? `<span class="summary-value">${escapeHtml(value)}</span>`
        : `<span class="summary-value empty">${escapeHtml(fallback)}</span>`;
    }

    function formatSummaryRow(label, value, fallback = "Not recorded for this job.") {
      return `
        <div class="summary-row">
          <strong>${escapeHtml(label)}</strong>
          ${formatPathValue(value, fallback)}
        </div>
      `;
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

    function renderReadableInspection(payload) {
      const infoLines = payload.info_lines || [];
      if (!infoLines.length) {
        inspectReadable.innerHTML = "<div class=\\"note\\">No additional media info lines were returned yet.</div>";
        return;
      }

      inspectReadable.innerHTML = `
        <ul>
          ${infoLines.map(line => `<li>${escapeHtml(line)}</li>`).join("")}
        </ul>
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
      const defaultOption = document.createElement("option");
      defaultOption.value = "default";
      defaultOption.textContent = "default: Default profile";
      presetSelect.appendChild(defaultOption);
      for (const preset of presets) {
        const option = document.createElement("option");
        option.value = preset.id;
        option.textContent = `${preset.kind}: ${preset.label}`;
        presetSelect.appendChild(option);
      }
      syncPresetSelection();
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
            <div class="summary-list">
              ${formatSummaryRow("Status", summary.status || "", "Unknown")}
              ${formatSummaryRow("Kind", summary.job_kind || "", "Unknown")}
              ${formatSummaryRow("Source", summary.source_label || "", "Unknown")}
              ${formatSummaryRow("Items", `${summary.items_done || 0}/${summary.items_total || 0}`, "0/0")}
              ${formatSummaryRow("Failed", String(summary.items_failed || 0), "0")}
              ${formatSummaryRow("Current item", summary.current_item_label || "", "No active item right now.")}
              ${formatSummaryRow("Download dir", summary.download_dir || "")}
              ${formatSummaryRow("Playlist dir", summary.playlist_dir || "")}
              ${formatSummaryRow("Results file", summary.results_path || "")}
            </div>
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
        const statusClass = escapeHtml(job.status || "queued");
        return `
          <button class="job-card${isActive}" type="button" data-job-id="${escapeHtml(job.job_id)}">
            <div class="job-card-head">
              <span class="job-card-title">${escapeHtml(job.job_kind || "download")} job</span>
              <span class="job-badge ${statusClass}">${escapeHtml(job.status || "queued")}</span>
            </div>
            <span class="job-card-subtitle">${escapeHtml(job.source_label || "")}</span>
            <div class="job-card-metrics">
              <span>${escapeHtml(job.items_done || 0)}/${escapeHtml(job.items_total || 0)} complete</span>
              <span>${escapeHtml(job.items_failed || 0)} failed</span>
              ${job.current_item_label ? `<span>Current: ${escapeHtml(job.current_item_label)}</span>` : ""}
            </div>
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

    applySessionButton.addEventListener("click", async () => {
      const state = await api("/api/session-config", {
        method: "POST",
        body: JSON.stringify({ updates: collectSessionUpdates() })
      });
      applySessionState(state);
      setActionMessage("Applied current form values to the session. Save Config if you want them written to disk.", "ok");
    });

    saveConfigButton.addEventListener("click", async () => {
      const payload = await api("/api/presets/save", {
        method: "POST",
        body: JSON.stringify({ save_config: "true" })
      });
      if (payload.state) {
        applySessionState(payload.state);
      }
      setActionMessage(
        payload.path
          ? `Saved session config to ${payload.path}.`
          : "Session config did not need to be written.",
        "ok"
      );
    });

    presetSelect.addEventListener("change", async () => {
      const state = await api("/api/presets/load", {
        method: "POST",
        body: JSON.stringify({ preset_id: presetSelect.value })
      });
      applySessionState(state);
      setActionMessage(`Loaded ${state.preset_details?.loaded_label || "default profile"} into the session.`, "ok");
    });

    for (const fieldId of sessionFieldIds) {
      document.getElementById(fieldId).addEventListener("input", refreshConfigFormState);
      document.getElementById(fieldId).addEventListener("change", refreshConfigFormState);
    }

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
      renderReadableInspection(payload);
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
