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
      max-width: 1100px;
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
    }
    .panel {
      padding: 18px;
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
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Python-YTRipper Web UI</h1>
      <p>
        This is the first working web shell for the downloader. It is intentionally simple:
        inspect a URL, tweak session settings, start a job, and watch the job list grow.
      </p>
    </section>

    <section class="grid">
      <div class="panel stack">
        <h2>Download</h2>
        <label for="url">YouTube URL</label>
        <input id="url" placeholder="https://www.youtube.com/watch?v=..." />
        <div class="row">
          <button id="inspect-btn" class="secondary" type="button">Inspect URL</button>
          <button id="download-btn" type="button">Start Job</button>
        </div>
        <p class="note">The current UI only supports one direct URL per job. Batch/file workflows can follow later.</p>
      </div>

      <div class="panel stack">
        <h2>Session Config</h2>
        <div class="row">
          <label><input id="audio-only" type="checkbox" /> Audio only</label>
          <label><input id="audio-mp3" type="checkbox" /> Convert to MP3</label>
          <label><input id="autotag" type="checkbox" /> Autotag</label>
          <label><input id="save-results" type="checkbox" /> Save results</label>
        </div>
        <div class="row">
          <div>
            <label for="download-dir">Download directory</label>
            <input id="download-dir" placeholder="~/Downloads/RipperDownloads" />
          </div>
          <div>
            <label for="preset-select">Load preset</label>
            <select id="preset-select"></select>
          </div>
        </div>
        <div class="row">
          <button id="save-config-btn" class="secondary" type="button">Save Config</button>
          <button id="apply-session-btn" type="button">Apply Session Settings</button>
        </div>
      </div>
    </section>

    <section class="grid">
      <div class="panel stack">
        <h2>Inspector</h2>
        <div id="inspect-output" class="status">No inspection yet.</div>
      </div>
      <div class="panel stack">
        <h2>Jobs</h2>
        <div id="jobs-output" class="status">No jobs yet.</div>
      </div>
    </section>
  </main>

  <script>
    const inspectOutput = document.getElementById("inspect-output");
    const jobsOutput = document.getElementById("jobs-output");
    const presetSelect = document.getElementById("preset-select");

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
      return {
        audio_only: document.getElementById("audio-only").checked,
        audio_mp3: document.getElementById("audio-mp3").checked,
        autotag: document.getElementById("autotag").checked,
        save_results: document.getElementById("save-results").checked,
        default_download_directory: document.getElementById("download-dir").value
      };
    }

    function applySessionState(state) {
      const options = state.options || {};
      document.getElementById("audio-only").checked = !!options.audio_only;
      document.getElementById("audio-mp3").checked = !!options.audio_mp3;
      document.getElementById("autotag").checked = !!options.autotag;
      document.getElementById("save-results").checked = !!options.save_results;
      document.getElementById("download-dir").value = options.default_download_directory || "";
    }

    async function loadSessionState() {
      const state = await api("/api/session-config");
      applySessionState(state);
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

    async function refreshJobs() {
      const jobs = await api("/api/jobs");
      if (!jobs.length) {
        jobsOutput.textContent = "No jobs yet.";
        return;
      }
      jobsOutput.textContent = jobs.map(job =>
        `${job.status} | ${job.job_kind} | ${job.items_done}/${job.items_total} | ${job.source_label}`
      ).join("\\n");
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

    document.getElementById("inspect-btn").addEventListener("click", async () => {
      const url = document.getElementById("url").value.trim();
      const payload = await api("/api/url/inspect", {
        method: "POST",
        body: JSON.stringify({ url, remote_check: true, fetch_info: true })
      });
      inspectOutput.textContent = JSON.stringify(payload, null, 2);
    });

    document.getElementById("download-btn").addEventListener("click", async () => {
      const url = document.getElementById("url").value.trim();
      await api("/api/jobs/download", {
        method: "POST",
        body: JSON.stringify({ url })
      });
      await refreshJobs();
    });

    loadSessionState().catch(error => { inspectOutput.textContent = String(error); });
    loadPresets().catch(error => { inspectOutput.textContent = String(error); });
    refreshJobs().catch(error => { jobsOutput.textContent = String(error); });
    setInterval(() => refreshJobs().catch(() => {}), 2000);
  </script>
</body>
</html>
"""
