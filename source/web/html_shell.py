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
      color-scheme: light;
      --bg: #f6f1e8;
      --panel: #fffaf2;
      --panel-soft: #fcf8f1;
      --panel-input: #fffdf9;
      --panel-active: #eef8f4;
      --ink-soft: #efe7d8;
      --ink: #20201c;
      --muted: #6d675e;
      --accent: #0e6b50;
      --accent-soft: #d7efe7;
      --border: #d5ccbd;
      --page-top: #f8f4ec;
      --page-glow: #f3dcc4;
      --shadow: rgba(32, 32, 28, 0.06);
      --success-surface: #dff2eb;
      --success-surface-soft: #eef8f4;
      --success-border: #badfd1;
      --success-ink: #184d3b;
      --warning-surface: #f4ecd8;
      --warning-surface-soft: #fbf3df;
      --warning-border: #d8c6a8;
      --warning-ink: #765c22;
      --danger-surface: #f6dddd;
      --danger-surface-soft: #fbefef;
      --danger-border: #dfbaba;
      --danger-ink: #7a3030;
      --path-surface: rgba(255, 253, 249, 0.75);
    }
    :root[data-theme="dark"] {
      color-scheme: dark;
      --bg: #171a20;
      --panel: #1f242c;
      --panel-soft: #252b34;
      --panel-input: #2a313b;
      --panel-active: #22372f;
      --ink-soft: #36404b;
      --ink: #ece7dd;
      --muted: #b7b0a4;
      --accent: #57ba96;
      --accent-soft: #2a4c42;
      --border: #3e4650;
      --page-top: #1b1f26;
      --page-glow: #2c3e37;
      --shadow: rgba(0, 0, 0, 0.28);
      --success-surface: #204438;
      --success-surface-soft: #1f3b33;
      --success-border: #3f7d69;
      --success-ink: #d6f1e6;
      --warning-surface: #4a4028;
      --warning-surface-soft: #3f3828;
      --warning-border: #7f7048;
      --warning-ink: #f2dfb1;
      --danger-surface: #4a2b31;
      --danger-surface-soft: #41282e;
      --danger-border: #7d555d;
      --danger-ink: #f0d6da;
      --path-surface: rgba(28, 34, 42, 0.78);
    }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, var(--page-glow) 0, transparent 32%),
        linear-gradient(180deg, var(--page-top) 0%, var(--bg) 100%);
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
      box-shadow: 0 8px 30px var(--shadow);
    }
    .hero {
      padding: 24px;
    }
    .hero-topbar {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }
    .hero-copy {
      min-width: 0;
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
    .health-topbar {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
      flex-wrap: wrap;
    }
    .health-summary-stack {
      display: grid;
      gap: 8px;
      min-width: 0;
    }
    .health-controls {
      display: grid;
      gap: 8px;
      justify-items: end;
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
      background: var(--panel-input);
      color: var(--ink);
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
      border: 1px solid var(--success-border);
    }
    button.inline-button {
      width: auto;
      min-width: 0;
      padding-inline: 14px;
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
      background: var(--panel-soft);
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
      background: var(--panel-soft);
      border-radius: 12px;
      padding: 10px 12px;
      text-align: left;
      color: var(--ink);
      min-width: 0;
    }
    .job-card.active {
      border-color: var(--accent);
      background: var(--panel-active);
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
      background: var(--ink-soft);
      color: var(--ink);
      white-space: nowrap;
    }
    .job-badge.completed,
    .job-badge.success {
      background: var(--success-surface);
      color: var(--success-ink);
    }
    .job-badge.failed {
      background: var(--danger-surface);
      color: var(--danger-ink);
    }
    .job-badge.partial,
    .job-badge.running,
    .job-badge.validating,
    .job-badge.queued {
      background: var(--warning-surface);
      color: var(--warning-ink);
    }
    .detail-grid {
      display: grid;
      gap: 10px;
      min-width: 0;
    }
    .detail-block {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--panel-soft);
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
    .health-summary-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .health-summary-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: var(--panel-soft);
      color: var(--muted);
      padding: 6px 10px;
      font-size: 0.84rem;
    }
    .health-summary-pill.ok {
      border-color: var(--success-border);
      background: var(--success-surface-soft);
      color: var(--success-ink);
    }
    .health-summary-pill.fail {
      border-color: var(--danger-border);
      background: var(--danger-surface-soft);
      color: var(--danger-ink);
    }
    .health-item {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--panel-soft);
      padding: 12px;
      min-width: 0;
      display: grid;
      gap: 8px;
    }
    .health-item.ok {
      border-color: var(--success-border);
      background: var(--success-surface-soft);
    }
    .health-item.fail {
      border-color: var(--danger-border);
      background: var(--danger-surface-soft);
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
    .health-item-head {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 10px;
    }
    .health-item-title {
      font-weight: 700;
      font-size: 0.94rem;
      color: var(--ink);
    }
    .health-item-body {
      display: grid;
      gap: 8px;
      min-width: 0;
    }
    .health-item-detail {
      display: grid;
      gap: 6px;
      min-width: 0;
    }
    .health-detail-label {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }
    .health-path {
      display: block;
      overflow: auto hidden;
      white-space: nowrap;
      border: 1px dashed var(--border);
      border-radius: 10px;
      background: var(--path-surface);
      padding: 8px 10px;
      font-family: "Courier New", monospace;
      font-size: 0.82rem;
      color: var(--ink);
    }
    .health-detail-list {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 0.85rem;
    }
    .health-summary {
      font-size: 0.92rem;
      color: var(--muted);
    }
    .health-reference,
    .health-meta {
      font-size: 0.84rem;
      color: var(--muted);
    }
    .pill {
      display: inline-block;
      width: auto;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.86rem;
      border: 1px solid var(--border);
      background: var(--panel-soft);
      color: var(--muted);
    }
    .pill.ok {
      border-color: var(--success-border);
      background: var(--success-surface-soft);
      color: var(--success-ink);
    }
    .pill.warn {
      border-color: var(--warning-border);
      background: var(--warning-surface-soft);
      color: var(--warning-ink);
    }
    .pill.fail {
      border-color: var(--danger-border);
      background: var(--danger-surface-soft);
      color: var(--danger-ink);
    }
    .action-banner {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--panel-soft);
      padding: 10px 12px;
      font-size: 0.9rem;
      color: var(--muted);
      overflow-wrap: anywhere;
    }
    .action-banner.ok {
      border-color: var(--success-border);
      background: var(--success-surface-soft);
      color: var(--success-ink);
    }
    .action-banner.fail {
      border-color: var(--danger-border);
      background: var(--danger-surface-soft);
      color: var(--danger-ink);
    }
    .action-banner.warn {
      border-color: var(--warning-border);
      background: var(--warning-surface-soft);
      color: var(--warning-ink);
    }
    .subtle-card {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--panel-soft);
      padding: 10px 12px;
      display: grid;
      gap: 6px;
      min-width: 0;
    }
    .subtle-card-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }
    .subtle-card-title {
      font-weight: 700;
      font-size: 0.92rem;
    }
    .subtle-card-body,
    .subtle-card-meta {
      font-size: 0.86rem;
      color: var(--muted);
      overflow-wrap: anywhere;
    }
    .subtle-card.ok {
      border-color: var(--success-border);
      background: var(--success-surface-soft);
    }
    .subtle-card.warn {
      border-color: var(--warning-border);
      background: var(--warning-surface-soft);
    }
    .field-note.ok {
      color: var(--success-ink);
    }
    .field-note.warn {
      color: var(--warning-ink);
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
      background: var(--panel-soft);
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
      background: var(--panel-soft);
      padding: 12px;
      font-size: 0.9rem;
      min-height: 0;
      overflow: auto;
    }
    .inspector-section {
      display: grid;
      gap: 10px;
      min-width: 0;
    }
    .inspector-caption {
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }
    .inspect-fact-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    }
    .inspect-fact {
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--panel);
      padding: 10px;
      display: grid;
      gap: 4px;
      min-width: 0;
    }
    .inspect-fact-label {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }
    .inspect-fact-value {
      font-size: 0.9rem;
      color: var(--ink);
      overflow-wrap: anywhere;
    }
    .inspect-preview-list {
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 6px;
    }
    .inspect-preview-note {
      font-size: 0.84rem;
      color: var(--muted);
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
      background: var(--panel-soft);
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
      .health-controls {
        justify-items: start;
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
      <div class="hero-topbar">
        <div class="hero-copy">
          <h1>Python-YTRipper Web UI</h1>
          <p>
            This is the first working web shell for the downloader. It is intentionally simple:
            inspect a video or playlist URL, tweak session settings, start a job, and watch the job list grow.
          </p>
        </div>
        <button id="theme-toggle-btn" class="secondary inline-button" type="button" aria-pressed="false">Dark Mode</button>
      </div>
    </section>

    <section class="panel health-grid">
      <div class="health-topbar">
        <div class="health-summary-stack">
          <h2>Health & Status</h2>
          <div id="health-summary" class="health-summary">Checking backend health...</div>
        </div>
        <div class="health-controls">
          <button id="health-refresh-btn" class="secondary inline-button" type="button">Refresh Health</button>
          <div id="health-checked-at" class="health-meta">No health check completed yet.</div>
        </div>
      </div>
      <div class="health-reference">Paths are shown for reference only. Browser-side folder opening stays deferred for now.</div>
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
        <div id="inspect-state" class="subtle-card">
          <div class="subtle-card-head">
            <div class="subtle-card-title">Inspection Guidance</div>
            <span id="inspect-state-pill" class="job-badge queued">Waiting</span>
          </div>
          <div id="inspect-state-body" class="subtle-card-body">
            Local validation runs automatically after a short pause. Inspect URL performs the deeper preview step.
          </div>
          <div id="inspect-state-meta" class="subtle-card-meta">
            Start Job needs a supported locally validated URL. Inspection is recommended, not required.
          </div>
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
            <div class="field-note">Loading a preset replaces the in-memory session immediately. Save Config controls what gets written back to disk.</div>
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
        <div id="preset-guidance" class="subtle-card">
          <div class="subtle-card-head">
            <div class="subtle-card-title">Preset Guidance</div>
            <span id="preset-guidance-pill" class="job-badge queued">Loading</span>
          </div>
          <div id="preset-guidance-body" class="subtle-card-body">
            Loading preset ownership and save behavior...
          </div>
          <div id="preset-guidance-meta" class="subtle-card-meta">
            Default, custom, and immutable presets will be explained here.
          </div>
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
          <div id="inspect-readable" class="inspector-readable">Quick facts and preview items will appear here after inspection.</div>
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
    const themeToggleButton = document.getElementById("theme-toggle-btn");
    const actionOutput = document.getElementById("action-output");
    const inspectSummary = document.getElementById("inspect-summary");
    const inspectReadable = document.getElementById("inspect-readable");
    const healthSummary = document.getElementById("health-summary");
    const healthOutput = document.getElementById("health-output");
    const healthRefreshButton = document.getElementById("health-refresh-btn");
    const healthCheckedAt = document.getElementById("health-checked-at");
    const inspectOutput = document.getElementById("inspect-output");
    const jobsOutput = document.getElementById("jobs-output");
    const jobDetailOutput = document.getElementById("job-detail-output");
    const inspectState = document.getElementById("inspect-state");
    const inspectStatePill = document.getElementById("inspect-state-pill");
    const inspectStateBody = document.getElementById("inspect-state-body");
    const inspectStateMeta = document.getElementById("inspect-state-meta");
    const presetSelect = document.getElementById("preset-select");
    const presetGuidance = document.getElementById("preset-guidance");
    const presetGuidancePill = document.getElementById("preset-guidance-pill");
    const presetGuidanceBody = document.getElementById("preset-guidance-body");
    const presetGuidanceMeta = document.getElementById("preset-guidance-meta");
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
    let presetCatalog = [];
    let lastInspection = null;
    const THEME_STORAGE_KEY = "python-ytripper-web-theme";
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

    function loadStoredTheme() {
      try {
        const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
        if (stored === "dark" || stored === "light") {
          return stored;
        }
      } catch (error) {
        // Ignore localStorage failures and fall back to system preference.
      }
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }

    function applyTheme(theme) {
      const resolved = theme === "dark" ? "dark" : "light";
      document.documentElement.dataset.theme = resolved;
      themeToggleButton.textContent = resolved === "dark" ? "Light Mode" : "Dark Mode";
      themeToggleButton.setAttribute("aria-pressed", resolved === "dark" ? "true" : "false");
    }

    function saveTheme(theme) {
      try {
        window.localStorage.setItem(THEME_STORAGE_KEY, theme);
      } catch (error) {
        // Ignore localStorage failures and keep the in-memory theme only.
      }
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

    function findPresetById(presetId) {
      return presetCatalog.find(preset => preset.id === presetId) || null;
    }

    function formatPresetOptionLabel(preset) {
      if (!preset) {
        return "Unknown preset";
      }
      if (preset.kind === "default") {
        return "Session default profile";
      }
      if (preset.kind === "custom") {
        return `${preset.label} (editable slot)`;
      }
      if (preset.kind === "immutable") {
        return `${preset.label} (read-only starter)`;
      }
      return `${preset.label} (${preset.kind})`;
    }

    function setPresetGuidanceCard(tone, label, body, meta) {
      presetGuidance.className = tone ? `subtle-card ${tone}` : "subtle-card";
      presetGuidancePill.className = `job-badge ${tone || "queued"}`;
      presetGuidancePill.textContent = label;
      presetGuidanceBody.textContent = body;
      presetGuidanceMeta.textContent = meta;
    }

    function renderPresetGuidance() {
      if (!currentSessionState) {
        setPresetGuidanceCard(
          "",
          "Loading",
          "Loading preset ownership and save behavior...",
          "Default, custom, and immutable presets will be explained here."
        );
        return;
      }

      const selectedPreset = findPresetById(presetSelect.value || "default");
      const loadedDetails = currentSessionState.preset_details || {};
      const loadedLabel = loadedDetails.loaded_label || "Default profile";
      const loadedKind = loadedDetails.loaded_kind || "default";
      const saveTargetLabel = loadedDetails.save_target_label || "Default profile";

      if (!selectedPreset || selectedPreset.kind === "default") {
        setPresetGuidanceCard(
          "ok",
          "Default",
          "The default profile is your normal working config on this machine. Loading it restores your standard saved settings.",
          `Current source: ${loadedLabel}. Save Config currently writes to ${saveTargetLabel}.`
        );
        return;
      }

      if (selectedPreset.kind === "custom") {
        setPresetGuidanceCard(
          "ok",
          "Custom",
          `${selectedPreset.label} is an editable user slot. Loading it replaces the session immediately, and Save Config writes back to that same slot when it stays the active source.`,
          `Current source: ${loadedLabel}. Selected load target: ${selectedPreset.label}.`
        );
        return;
      }

      if (selectedPreset.kind === "immutable") {
        setPresetGuidanceCard(
          "warn",
          "Read-only starter",
          `${selectedPreset.label} is an immutable starter preset. It is useful for one-shot setups, but Save Config will write your later edits to ${saveTargetLabel} instead of overwriting the preset itself.`,
          `Current source: ${loadedLabel}. Selected load target: ${selectedPreset.label}.`
        );
        return;
      }

      setPresetGuidanceCard(
        "",
        "Preset",
        `${selectedPreset.label} can be loaded into the current session.`,
        `Current source: ${loadedLabel}. Save target: ${saveTargetLabel}.`
      );
    }

    function syncPresetSelection() {
      if (!currentSessionState) {
        return;
      }
      const loadedId = currentSessionState.preset_details?.loaded_id || "default";
      presetSelect.value = loadedId;
      renderPresetGuidance();
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
        ? `Loaded source: ${loadedLabel} preset. Immutable presets are read-only starters, so Save Config writes later edits to ${saveTargetLabel}.`
        : loadedKind === "custom"
          ? `Loaded source: ${loadedLabel}. Save Config writes back to this custom slot while it remains active.`
          : `Loaded source: ${loadedLabel}. Save Config writes to this default working profile.`;
      const saveTone = configSync.has_unsaved_changes ? "warn" : "ok";
      const savePath = presetDetails.save_target_path || "";

      setBanner(configSourceBanner, sourceMessage, loadedKind === "immutable" ? "warn" : "ok");
      setBanner(
        configSyncBanner,
        `${configSync.status_label || `Save Config writes to ${saveTargetLabel}.`}${savePath ? ` Target: ${savePath}` : ""}`,
        saveTone
      );
      saveConfigButton.disabled = false;
      syncPresetSelection();
      refreshConfigFormState();
      renderPresetGuidance();
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

    function formatHealthName(name) {
      const names = {
        ffmpeg_binary: "FFmpeg binary",
        config_directory: "Config directory",
        web_runtime_directory: "Web runtime directory",
        default_download_directory: "Default download directory",
        python_dependencies: "Python dependencies",
      };
      return names[name] || String(name || "Health check").replaceAll("_", " ");
    }

    function renderHealthItemDetails(item) {
      const details = item.details || {};
      const blocks = [];
      const path = details.path ? `
        <div class="health-item-detail">
          <div class="health-detail-label">Path</div>
          <code class="health-path">${escapeHtml(details.path)}</code>
        </div>
      ` : "";
      if (path) {
        blocks.push(path);
      }

      if (Array.isArray(details.checked) && details.checked.length) {
        blocks.push(`
          <div class="health-item-detail">
            <div class="health-detail-label">Checked</div>
            <ul class="health-detail-list">
              ${details.checked.map(entry => `<li>${escapeHtml(entry)}</li>`).join("")}
            </ul>
          </div>
        `);
      }

      if (Array.isArray(details.missing) && details.missing.length) {
        blocks.push(`
          <div class="health-item-detail">
            <div class="health-detail-label">Missing</div>
            <ul class="health-detail-list">
              ${details.missing.map(entry => `<li>${escapeHtml(entry)}</li>`).join("")}
            </ul>
          </div>
        `);
      }

      if (details.error) {
        blocks.push(`
          <div class="health-item-detail">
            <div class="health-detail-label">Error</div>
            <span>${escapeHtml(details.error)}</span>
          </div>
        `);
      }

      if (!blocks.length) {
        const fallback = formatHealthDetails(details);
        return fallback ? `<div class="health-item-detail"><span>${escapeHtml(fallback)}</span></div>` : "";
      }

      return blocks.join("");
    }

    async function refreshHealth() {
      healthRefreshButton.disabled = true;
      const payload = await api("/api/health");
      const items = payload.items || [];
      const passingCount = items.filter(item => item.ok).length;
      const failingCount = items.length - passingCount;

      healthSummary.innerHTML = `
        <div>${payload.ok
          ? `Backend ready. ${items.length} checks passed.`
          : `Backend needs attention. ${passingCount}/${items.length} checks passed.`}</div>
        <div class="health-summary-pills">
          <span class="health-summary-pill ok">${escapeHtml(String(passingCount))} passing</span>
          <span class="health-summary-pill ${failingCount ? "fail" : ""}">${escapeHtml(String(failingCount))} issues</span>
        </div>
      `;
      healthCheckedAt.textContent = `Last checked at ${new Date().toLocaleTimeString()}.`;

      healthOutput.innerHTML = items.map(item => {
        const itemClass = item.ok ? "ok" : "fail";
        const detailMarkup = renderHealthItemDetails(item);
        return `
          <div class="health-item ${itemClass}">
            <div class="health-item-head">
              <div class="health-item-title">${escapeHtml(formatHealthName(item.name || ""))}</div>
              <span class="job-badge ${item.ok ? "completed" : "failed"}">${item.ok ? "OK" : "Issue"}</span>
            </div>
            <div class="health-item-body">
              <span>${escapeHtml(item.message || "")}</span>
              ${detailMarkup}
            </div>
          </div>
        `;
      }).join("");
      healthRefreshButton.disabled = false;
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
      const summaryUrl = payload.url || payload.cleaned_url || payload.normalized_url || "";
      const checkedAtLabel = lastInspection?.url === summaryUrl
        ? lastInspection.checkedAtLabel
        : "";

      inspectSummary.innerHTML = `
        <strong>${escapeHtml(payload.title || "Inspection ready")}</strong>
        <span>${escapeHtml(typeLabel)} | ${escapeHtml(accessLabel)} | Items: ${escapeHtml(itemCountLabel)}</span>
        <span>${escapeHtml(payload.cleaned_url || payload.normalized_url || payload.url || "")}</span>
        ${checkedAtLabel ? `<span>Inspected at ${escapeHtml(checkedAtLabel)}</span>` : ""}
      `;
    }

    function cleanInspectionLine(line) {
      return String(line || "")
        .trim()
        .replace(/,$/, "")
        .replace(/^["']|["']$/g, "")
        .trim();
    }

    function buildInspectionPreview(payload) {
      const cleanedLines = (payload.info_lines || [])
        .map(cleanInspectionLine)
        .filter(Boolean);
      const previewItems = [];
      const extraLines = [];

      for (const line of cleanedLines) {
        if (/^videos:$/i.test(line)) {
          continue;
        }

        if (/^\\d+\\.\\s+/.test(line)) {
          previewItems.push(line.replace(/^\\d+\\.\\s+/, ""));
          continue;
        }

        if (/^(playlist title|number of videos):/i.test(line)) {
          continue;
        }

        extraLines.push(line);
      }

      return {
        previewItems,
        extraLines,
      };
    }

    function renderReadableInspection(payload) {
      const preview = buildInspectionPreview(payload);
      const checkedAtLabel = lastInspection?.url === (payload.url || payload.cleaned_url || payload.normalized_url || "")
        ? lastInspection.checkedAtLabel
        : "Just now";
      const facts = [
        { label: "Type", value: payload.is_playlist ? "Playlist" : "Video" },
        { label: "Access", value: payload.remote_checked ? (payload.remotely_accessible ? "Reachable" : "Not reachable") : "Local only" },
        { label: "Items", value: payload.item_count == null ? "Unknown" : String(payload.item_count) },
        { label: "Checked", value: checkedAtLabel },
      ];

      const previewMarkup = preview.previewItems.length
        ? `
          <div class="inspector-section">
            <div class="inspector-caption">${payload.is_playlist ? "Preview items" : "Preview details"}</div>
            <ol class="inspect-preview-list">
              ${preview.previewItems.slice(0, 6).map(item => `<li>${escapeHtml(item)}</li>`).join("")}
            </ol>
            ${payload.is_playlist && payload.item_count && payload.item_count > preview.previewItems.length
              ? `<div class="inspect-preview-note">Showing ${escapeHtml(String(Math.min(6, preview.previewItems.length)))} of ${escapeHtml(String(payload.item_count))} discovered entries in the preview.</div>`
              : ""}
          </div>
        `
        : "";

      const extraMarkup = preview.extraLines.length
        ? `
          <div class="inspector-section">
            <div class="inspector-caption">Additional info</div>
            <ul>
              ${preview.extraLines.map(line => `<li>${escapeHtml(line)}</li>`).join("")}
            </ul>
          </div>
        `
        : "";

      if (!previewMarkup && !extraMarkup) {
        inspectReadable.innerHTML = `
          <div class="inspector-section">
            <div class="inspector-caption">Quick scan</div>
            <div class="inspect-fact-grid">
              ${facts.map(fact => `
                <div class="inspect-fact">
                  <div class="inspect-fact-label">${escapeHtml(fact.label)}</div>
                  <div class="inspect-fact-value">${escapeHtml(fact.value)}</div>
                </div>
              `).join("")}
            </div>
            <div class="inspect-preview-note">No additional media info lines were returned yet.</div>
          </div>
        `;
        return;
      }

      inspectReadable.innerHTML = `
        <div class="inspector-section">
          <div class="inspector-caption">Quick scan</div>
          <div class="inspect-fact-grid">
            ${facts.map(fact => `
              <div class="inspect-fact">
                <div class="inspect-fact-label">${escapeHtml(fact.label)}</div>
                <div class="inspect-fact-value">${escapeHtml(fact.value)}</div>
              </div>
            `).join("")}
          </div>
        </div>
        ${previewMarkup}
        ${extraMarkup}
      `;
    }

    function setInspectionGuidance(statusClass, label, body, meta) {
      inspectState.className = `subtle-card ${statusClass || ""}`.trim();
      inspectStatePill.className = `job-badge ${statusClass || "queued"}`;
      inspectStatePill.textContent = label;
      inspectStateBody.textContent = body;
      inspectStateMeta.textContent = meta;
    }

    function refreshInspectionGuidance() {
      const currentUrl = urlInput.value.trim();
      if (!currentUrl) {
        setInspectionGuidance(
          "queued",
          "Waiting",
          "Local validation runs automatically after a short pause. Inspect URL performs the deeper preview step.",
          "Start Job needs a supported locally validated URL. Inspection is recommended, not required."
        );
        return;
      }

      if (!currentUrlValidation.valid || currentUrlValidation.url !== currentUrl) {
        setInspectionGuidance(
          "validating",
          "Validate",
          "Wait for the local URL check to finish before inspecting or starting a job.",
          "The checkmark-style validation happens automatically after a short pause in typing."
        );
        return;
      }

      if (!lastInspection) {
        setInspectionGuidance(
          "partial",
          "Preview recommended",
          currentUrlValidation.isPlaylist
            ? "This playlist URL is locally valid. Inspect URL can fetch a title and rough item preview before download."
            : "This video URL is locally valid. Inspect URL can fetch a title and accessibility preview before download.",
          "Start Job is already available because local validation passed."
        );
        return;
      }

      if (lastInspection.url !== currentUrl) {
        setInspectionGuidance(
          "partial",
          "Stale preview",
          "The current input differs from the last inspected URL. Re-run Inspect URL if you want the Inspector panel to match this input.",
          `Last inspected at ${lastInspection.checkedAtLabel}. Start Job still uses the URL currently in the input field.`
        );
        return;
      }

      if (lastInspection.error) {
        setInspectionGuidance(
          "failed",
          "Inspection issue",
          "The current URL matches the last inspected input, but the remote inspection reported a problem.",
          `Last inspected at ${lastInspection.checkedAtLabel}. You can retry Inspect URL or start anyway if local validation is enough for this run.`
        );
        return;
      }

      const itemLabel = lastInspection.itemCount == null
        ? "item count unknown"
        : `${lastInspection.itemCount} ${lastInspection.isPlaylist ? "items" : "item"}`;
      setInspectionGuidance(
        "completed",
        "Preview ready",
        lastInspection.title
          ? `Inspection matches the current URL: ${lastInspection.title}.`
          : "Inspection matches the current URL.",
        `Checked at ${lastInspection.checkedAtLabel}. ${lastInspection.isPlaylist ? "Playlist" : "Video"} preview loaded with ${itemLabel}.`
      );
    }

    function updateUrlControls() {
      const hasUrl = !!urlInput.value.trim();
      const sameUrl = currentUrlValidation.url === urlInput.value.trim();
      const canUseUrl = hasUrl && sameUrl && currentUrlValidation.valid;
      inspectButton.disabled = !hasUrl;
      downloadButton.disabled = !canUseUrl;
      refreshInspectionGuidance();
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
      presetCatalog = [
        {
          id: "default",
          kind: "default",
          label: "Default profile",
        },
        ...presets,
      ];
      presetSelect.innerHTML = "";
      const defaultOption = document.createElement("option");
      defaultOption.value = "default";
      defaultOption.textContent = "default: Session default profile";
      presetSelect.appendChild(defaultOption);
      for (const preset of presets) {
        const option = document.createElement("option");
        option.value = preset.id;
        option.textContent = `${preset.kind}: ${formatPresetOptionLabel(preset)}`;
        presetSelect.appendChild(option);
      }
      syncPresetSelection();
      renderPresetGuidance();
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
      renderPresetGuidance();
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

    themeToggleButton.addEventListener("click", () => {
      const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
      saveTheme(nextTheme);
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
      lastInspection = {
        url,
        title: payload.title || "",
        error: payload.error || "",
        isPlaylist: !!payload.is_playlist,
        itemCount: payload.item_count == null ? null : payload.item_count,
        checkedAtLabel: new Date().toLocaleTimeString(),
      };
      setActionMessage(
        payload.title
          ? `Inspection loaded: ${payload.title}`
          : "Inspection completed.",
        payload.error ? "fail" : "ok"
      );
      renderInspectionSummary(payload);
      renderReadableInspection(payload);
      inspectOutput.textContent = JSON.stringify(payload, null, 2);
      refreshInspectionGuidance();
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
        lastInspection && lastInspection.url === url
          ? `Started ${job.job_kind || "download"} job ${job.job_id} for ${job.source_label || url}.`
          : `Started ${job.job_kind || "download"} job ${job.job_id} for ${job.source_label || url}. No fresh inspection preview was loaded for this exact URL.`,
        "ok"
      );
      await refreshJobs();
    });

    refreshHealth().catch(error => {
      healthSummary.textContent = "Backend health could not be loaded.";
      healthOutput.innerHTML = `<div class="status">${escapeHtml(String(error))}</div>`;
      healthCheckedAt.textContent = "Health refresh failed.";
      healthRefreshButton.disabled = false;
    });
    healthRefreshButton.addEventListener("click", () => {
      refreshHealth().catch(error => {
        healthSummary.textContent = "Backend health could not be loaded.";
        healthOutput.innerHTML = `<div class="status">${escapeHtml(String(error))}</div>`;
        healthCheckedAt.textContent = "Health refresh failed.";
        healthRefreshButton.disabled = false;
      });
    });
    applyTheme(loadStoredTheme());
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
