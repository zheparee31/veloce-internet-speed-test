"""A small Flask web speed test that runs on local, LAN, or public networks."""

from __future__ import annotations

import argparse
import re
import shutil
import socket
import subprocess
import threading

from flask import Flask, Response, jsonify, request


MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 64 * 1024

PAGE = r"""<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#080d18">
  <title>Veloce — Internet Speed Test</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #080d18;
      --surface: #111a29;
      --surface-raised: #172336;
      --surface-soft: rgba(255, 255, 255, .035);
      --line: rgba(183, 204, 232, .12);
      --text: #f1f6ff;
      --muted: #93a4bd;
      --faint: #65758d;
      --mint: #57e5b2;
      --blue: #70a7ff;
      --orange: #ffad5c;
      --red: #ff6d7f;
      --shadow: 0 28px 80px rgba(0, 0, 0, .32);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      font-synthesis: none;
    }
    :root[data-theme="light"] {
      color-scheme: light;
      --bg: #edf2f8;
      --surface: #fff;
      --surface-raised: #f3f7fc;
      --surface-soft: rgba(21, 42, 70, .035);
      --line: rgba(31, 53, 82, .13);
      --text: #152238;
      --muted: #586a82;
      --faint: #77879c;
      --shadow: 0 24px 72px rgba(39, 59, 88, .14);
    }
    * { box-sizing: border-box; }
    body {
      min-height: 100vh;
      margin: 0;
      padding: 34px 18px 50px;
      background:
        radial-gradient(ellipse at 50% -10%, rgba(63, 139, 255, .20), transparent 40%),
        var(--bg);
      transition: background-color .2s ease, color .2s ease;
    }
    button, select { font: inherit; }
    button { color: inherit; }
    button:focus-visible, select:focus-visible {
      outline: 3px solid var(--mint);
      outline-offset: 3px;
    }
    main { width: min(1040px, 100%); margin: 0 auto; }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 24px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 11px;
      color: var(--muted);
      font-size: .77rem;
      font-weight: 800;
      letter-spacing: .17em;
      text-transform: uppercase;
    }
    .brand-mark {
      display: grid;
      width: 37px;
      height: 37px;
      place-items: center;
      border: 1px solid rgba(87, 229, 178, .34);
      border-radius: 12px;
      color: var(--mint);
      background: rgba(87, 229, 178, .08);
    }
    .brand-mark svg { width: 22px; height: 22px; }
    .top-actions { display: flex; align-items: center; gap: 9px; }
    .icon-button {
      display: grid;
      width: 40px;
      height: 40px;
      place-items: center;
      border: 1px solid var(--line);
      border-radius: 13px;
      color: var(--muted);
      background: var(--surface-soft);
      cursor: pointer;
      transition: color .15s ease, border-color .15s ease, transform .15s ease;
    }
    .icon-button:hover { color: var(--text); border-color: var(--mint); transform: translateY(-1px); }
    .icon-button svg { width: 18px; height: 18px; }
    .connection-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 36px;
      padding: 0 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      background: var(--surface-soft);
      font-size: .75rem;
      font-weight: 650;
    }
    .connection-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--mint);
      box-shadow: 0 0 12px rgba(87, 229, 178, .65);
    }
    .connection-dot.offline { background: var(--red); box-shadow: none; }
    .hero { margin-bottom: 26px; }
    .eyebrow {
      margin: 0 0 9px;
      color: var(--mint);
      font-size: .72rem;
      font-weight: 800;
      letter-spacing: .16em;
      text-transform: uppercase;
    }
    h1 { margin: 0; font-size: clamp(2rem, 5vw, 3.25rem); letter-spacing: -.055em; line-height: 1.08; }
    .hero-copy { max-width: 650px; margin: 12px 0 0; color: var(--muted); line-height: 1.7; }
    .dashboard {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(300px, .85fr);
      gap: 18px;
      align-items: stretch;
    }
    .card {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 23px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }
    .gauge-card {
      position: relative;
      display: flex;
      min-height: 480px;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      padding: 26px;
    }
    .gauge-card::before {
      position: absolute;
      top: -120px;
      left: 50%;
      width: 380px;
      height: 300px;
      border-radius: 50%;
      background: rgba(87, 229, 178, .055);
      content: "";
      filter: blur(50px);
      transform: translateX(-50%);
      pointer-events: none;
    }
    .gauge-heading {
      z-index: 1;
      display: flex;
      width: min(460px, 100%);
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: -8px;
    }
    .gauge-title { margin: 0; color: var(--muted); font-size: .76rem; font-weight: 800; letter-spacing: .14em; }
    .live-label { color: var(--faint); font-size: .72rem; }
    .gauge-wrap { position: relative; width: min(470px, 100%); }
    .gauge-svg { display: block; width: 100%; overflow: visible; }
    .gauge-track {
      fill: none;
      stroke: var(--surface-raised);
      stroke-linecap: round;
      stroke-width: 13;
    }
    .gauge-active {
      fill: none;
      stroke: url(#gaugeGradient);
      stroke-dasharray: 0 1000;
      stroke-linecap: round;
      stroke-width: 13;
      transition: stroke-dasharray .35s ease;
    }
    .gauge-tick { stroke: var(--faint); stroke-linecap: round; stroke-width: 2; opacity: .75; }
    .gauge-tick.major { stroke: var(--text); stroke-width: 3; opacity: .95; }
    .gauge-number { fill: var(--muted); font-size: 11px; font-weight: 700; text-anchor: middle; }
    .gauge-unit-label { fill: var(--faint); font-size: 9px; font-weight: 700; letter-spacing: 1.2px; text-anchor: middle; }
    .needle {
      fill: var(--mint);
      filter: drop-shadow(0 0 6px rgba(87, 229, 178, .55));
      transition: transform .35s cubic-bezier(.2, .8, .25, 1);
    }
    .needle-hub { fill: var(--text); stroke: var(--mint); stroke-width: 4; }
    .gauge-readout {
      position: absolute;
      right: 0;
      bottom: 4%;
      left: 0;
      display: grid;
      justify-items: center;
      text-align: center;
      pointer-events: none;
    }
    .gauge-speed {
      font-size: clamp(3.4rem, 10vw, 5.4rem);
      font-variant-numeric: tabular-nums;
      font-weight: 780;
      letter-spacing: -.08em;
      line-height: .95;
    }
    .gauge-unit { margin-top: 9px; color: var(--muted); font-size: .76rem; font-weight: 750; letter-spacing: .15em; }
    .gauge-mode { margin-top: 9px; color: var(--mint); font-size: .72rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
    .phase-row { z-index: 1; display: flex; width: min(460px, 100%); justify-content: space-between; gap: 8px; margin-top: 5px; }
    .phase {
      display: flex;
      align-items: center;
      gap: 7px;
      color: var(--faint);
      font-size: .71rem;
      font-weight: 750;
      letter-spacing: .06em;
    }
    .phase-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--surface-raised); }
    .phase.active { color: var(--text); }
    .phase.active .phase-dot { background: var(--mint); box-shadow: 0 0 10px rgba(87, 229, 178, .65); }
    .gauge-controls { z-index: 1; display: grid; width: min(460px, 100%); grid-template-columns: 1fr auto; gap: 10px; margin-top: 25px; }
    .primary-button, .secondary-button, .quiet-button {
      min-height: 48px;
      border: 1px solid transparent;
      border-radius: 14px;
      font-weight: 800;
      cursor: pointer;
      transition: transform .15s ease, filter .15s ease, border-color .15s ease;
    }
    .primary-button {
      color: #07150f;
      background: var(--mint);
      box-shadow: 0 10px 24px rgba(87, 229, 178, .18);
    }
    .primary-button:hover:not(:disabled) { transform: translateY(-2px); filter: brightness(1.05); }
    .primary-button:disabled { cursor: wait; opacity: .65; }
    .secondary-button {
      padding: 0 16px;
      border-color: var(--line);
      color: var(--muted);
      background: var(--surface-soft);
    }
    .secondary-button:hover:not(:disabled), .quiet-button:hover:not(:disabled) { border-color: var(--mint); color: var(--text); }
    .secondary-button:disabled { cursor: not-allowed; opacity: .45; }
    .test-status { min-height: 1.5em; margin: 14px 0 0; color: var(--muted); font-size: .81rem; text-align: center; }
    .progress-track { width: min(460px, 100%); height: 4px; overflow: hidden; border-radius: 9px; background: var(--surface-raised); }
    .progress-fill { width: 0; height: 100%; border-radius: inherit; background: var(--mint); transition: width .3s ease; }
    .side-stack { display: grid; grid-template-rows: auto 1fr; gap: 18px; }
    .settings-card, .metrics-card, .history-card { padding: 23px; }
    .section-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    h2 { margin: 0; font-size: 1rem; letter-spacing: -.02em; }
    .section-caption { margin: 7px 0 0; color: var(--muted); font-size: .78rem; line-height: 1.5; }
    .settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 11px; margin-top: 18px; }
    .setting-label { display: grid; gap: 7px; color: var(--muted); font-size: .72rem; font-weight: 700; }
    select {
      width: 100%;
      min-height: 42px;
      padding: 0 10px;
      border: 1px solid var(--line);
      border-radius: 11px;
      color: var(--text);
      background: var(--surface-raised);
    }
    .setting-hint { grid-column: 1 / -1; margin: 1px 0 0; color: var(--faint); font-size: .7rem; line-height: 1.5; }
    .metric-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 17px; }
    .metric {
      min-width: 0;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 15px;
      background: var(--surface-soft);
    }
    .metric-label { color: var(--muted); font-size: .67rem; font-weight: 800; letter-spacing: .1em; }
    .metric-value { margin-top: 9px; font-size: clamp(1.4rem, 4vw, 1.95rem); font-variant-numeric: tabular-nums; font-weight: 760; letter-spacing: -.055em; }
    .metric-unit { margin-left: 5px; color: var(--faint); font-size: .68rem; font-weight: 650; letter-spacing: 0; }
    .metric-sub { margin-top: 4px; color: var(--faint); font-size: .67rem; }
    .quality-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 13px; }
    .quality-label { color: var(--muted); font-size: .75rem; }
    .quality-value { color: var(--mint); font-size: .78rem; font-weight: 800; }
    .quality-track { height: 5px; margin-top: 9px; overflow: hidden; border-radius: 9px; background: var(--surface-raised); }
    .quality-fill { width: 0; height: 100%; border-radius: inherit; background: var(--mint); transition: width .4s ease, background .3s ease; }
    .history-card { margin-top: 18px; }
    .history-actions { display: flex; flex-wrap: wrap; gap: 7px; }
    .quiet-button { min-height: 34px; padding: 0 11px; border-color: var(--line); border-radius: 10px; color: var(--muted); background: transparent; font-size: .7rem; }
    .chart-wrap { height: 170px; margin-top: 16px; }
    #historyChart { display: block; width: 100%; height: 100%; }
    .chart-legend { display: flex; justify-content: center; gap: 20px; margin: 3px 0 15px; color: var(--muted); font-size: .68rem; }
    .legend-item { display: inline-flex; align-items: center; gap: 7px; }
    .legend-mark { width: 8px; height: 8px; border-radius: 50%; }
    .history-empty { display: grid; min-height: 150px; place-items: center; color: var(--faint); font-size: .8rem; text-align: center; }
    .history-list { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
    .history-item {
      display: grid;
      grid-template-columns: minmax(105px, 1.2fr) repeat(3, minmax(60px, .8fr)) auto;
      align-items: center;
      gap: 8px;
      padding: 12px 10px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-soft);
      font-size: .72rem;
    }
    .history-date { color: var(--muted); }
    .history-number { font-variant-numeric: tabular-nums; font-weight: 750; }
    .history-number small { display: block; margin-bottom: 3px; color: var(--faint); font-size: .59rem; font-weight: 650; letter-spacing: .07em; }
    .delete-result {
      display: grid;
      width: 28px;
      height: 28px;
      place-items: center;
      border: 0;
      border-radius: 8px;
      color: var(--faint);
      background: transparent;
      cursor: pointer;
    }
    .delete-result:hover { color: var(--red); background: rgba(255, 109, 127, .09); }
    .footer-note { margin: 22px auto 0; color: var(--faint); font-size: .72rem; line-height: 1.65; text-align: center; }
    .toast {
      position: fixed;
      right: 20px;
      bottom: 20px;
      z-index: 5;
      max-width: min(360px, calc(100% - 40px));
      padding: 13px 16px;
      border: 1px solid var(--line);
      border-radius: 13px;
      color: var(--text);
      background: var(--surface-raised);
      box-shadow: var(--shadow);
      opacity: 0;
      pointer-events: none;
      transform: translateY(8px);
      transition: opacity .18s ease, transform .18s ease;
    }
    .toast.visible { opacity: 1; transform: translateY(0); }
    @media (max-width: 820px) {
      .dashboard { grid-template-columns: 1fr; }
      .side-stack { grid-template-columns: 1fr 1fr; grid-template-rows: auto; align-items: stretch; }
      .metrics-card { min-height: 0; }
      .gauge-card { min-height: 450px; }
      .history-card { margin-top: 18px; }
    }
    @media (max-width: 580px) {
      body { padding: 22px 12px 38px; }
      .topbar { align-items: flex-start; }
      .connection-pill { display: none; }
      .brand { font-size: .68rem; letter-spacing: .12em; }
      .hero-copy { font-size: .9rem; }
      .gauge-card { min-height: 390px; padding: 20px 14px; }
      .gauge-heading, .phase-row, .gauge-controls { width: 100%; }
      .gauge-wrap { width: min(420px, 115%); margin: 0 -7%; }
      .gauge-readout { bottom: 1%; }
      .gauge-speed { font-size: clamp(3.2rem, 16vw, 4.8rem); }
      .phase { gap: 5px; font-size: .62rem; }
      .gauge-controls { grid-template-columns: 1fr auto; }
      .side-stack { grid-template-columns: 1fr; }
      .settings-card, .metrics-card, .history-card { padding: 19px; }
      .history-item { grid-template-columns: minmax(90px, 1fr) repeat(3, minmax(48px, .7fr)) auto; gap: 5px; padding: 10px 7px; font-size: .65rem; }
      .history-date { font-size: .62rem; }
      .history-number small { font-size: .54rem; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; }
    }
  </style>
</head>
<body>
  <main>
    <header class="topbar">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M4 16.5a11 11 0 0 1 16 0M7 13a7 7 0 0 1 10 0m-7-3.5a3 3 0 0 1 4 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <circle cx="12" cy="19" r="1.5" fill="currentColor"/>
          </svg>
        </span>
        <span>Veloce <span style="color:var(--mint)">/</span> Speed lab</span>
      </div>
      <div class="top-actions">
        <div class="connection-pill" title="Status koneksi browser">
          <span class="connection-dot" id="connectionDot"></span>
          <span id="connectionLabel">Memeriksa koneksi</span>
        </div>
        <button class="icon-button" id="themeToggle" type="button" aria-label="Ganti tema" title="Ganti tema">
          <svg id="themeIcon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M20.5 15.3A8.5 8.5 0 0 1 8.7 3.5 8.5 8.5 0 1 0 20.5 15.3Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </header>

    <section class="hero">
      <p class="eyebrow">Tes koneksi · <span id="testCount">0</span> pengukuran tersimpan</p>
      <h1>Seberapa kencang<br>koneksi kamu?</h1>
      <p class="hero-copy">Putar gasnya. Ukur kecepatan download, upload, ping, dan kestabilan koneksi dari perangkat ini langsung ke server.</p>
    </section>

    <section class="dashboard" aria-label="Dashboard tes kecepatan">
      <section class="card gauge-card" aria-label="Speedometer kecepatan saat ini">
        <div class="gauge-heading">
          <h2 class="gauge-title">LIVE SPEEDOMETER</h2>
          <span class="live-label" id="gaugeCaption">Siap mengukur</span>
        </div>
        <div class="gauge-wrap">
          <svg class="gauge-svg" id="gaugeSvg" viewBox="0 0 320 210" role="img" aria-labelledby="gaugeTitle gaugeDescription">
            <title id="gaugeTitle">Speedometer internet bergaya analog</title>
            <desc id="gaugeDescription">Jarum bergerak mengikuti kecepatan unduh atau unggah yang sedang diukur.</desc>
            <defs>
              <linearGradient id="gaugeGradient" x1="0" x2="1" y1="0" y2="0">
                <stop offset="0%" stop-color="#70a7ff"/>
                <stop offset="58%" stop-color="#57e5b2"/>
                <stop offset="100%" stop-color="#ffad5c"/>
              </linearGradient>
            </defs>
            <path class="gauge-track" d="M 48 164 A 112 112 0 1 1 272 164"/>
            <path class="gauge-active" id="gaugeArc" d="M 48 164 A 112 112 0 1 1 272 164"/>
            <g id="gaugeTicks" aria-hidden="true"></g>
            <g id="needle" transform="rotate(-130 160 164)">
              <path class="needle" d="M 160 164 L 156.5 164 L 158.3 59 Q 160 50 161.7 59 L 163.5 164 Z"/>
            </g>
            <circle class="needle-hub" cx="160" cy="164" r="8"/>
            <text class="gauge-unit-label" x="160" y="190">MEGABIT / DETIK</text>
          </svg>
          <div class="gauge-readout" aria-live="polite">
            <span class="gauge-speed" id="gaugeValue">0.0</span>
            <span class="gauge-unit">Mbps</span>
            <span class="gauge-mode" id="gaugeMode">Siap</span>
          </div>
        </div>
        <div class="phase-row" aria-label="Tahapan tes">
          <span class="phase" id="phasePing"><span class="phase-dot"></span> PING</span>
          <span class="phase" id="phaseDownload"><span class="phase-dot"></span> DOWNLOAD</span>
          <span class="phase" id="phaseUpload"><span class="phase-dot"></span> UPLOAD</span>
          <span class="phase" id="phaseDone"><span class="phase-dot"></span> SELESAI</span>
        </div>
        <div class="gauge-controls">
          <button class="primary-button" id="startButton" type="button">Mulai tes kecepatan</button>
          <button class="secondary-button" id="cancelButton" type="button" disabled>Batalkan</button>
        </div>
        <div class="progress-track" role="progressbar" aria-label="Progres tes" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" style="margin-top:14px">
          <div class="progress-fill" id="progressFill"></div>
        </div>
        <p class="test-status" id="testStatus" role="status" aria-live="polite">Siap. Pilih profil tes lalu mulai.</p>
      </section>

      <div class="side-stack">
        <section class="card settings-card" aria-labelledby="settingsTitle">
          <div class="section-title-row">
            <h2 id="settingsTitle">Pengaturan tes</h2>
            <span class="live-label">SESUAIKAN</span>
          </div>
          <p class="section-caption">Atur besar data tes agar cocok dengan kecepatan koneksi.</p>
          <div class="settings-grid">
            <label class="setting-label" for="testProfile">
              Profil pengujian
              <select id="testProfile">
                <option value="quick">Cepat · 3 / 1 MB</option>
                <option value="balanced" selected>Seimbang · 10 / 5 MB</option>
                <option value="precise">Presisi · 20 / 10 MB</option>
              </select>
            </label>
            <label class="setting-label" for="pingSamples">
              Sampel ping
              <select id="pingSamples">
                <option value="5">5 sampel</option>
                <option value="10" selected>10 sampel</option>
                <option value="15">15 sampel</option>
              </select>
            </label>
            <p class="setting-hint">Profil lebih besar biasanya menghasilkan pengukuran kecepatan yang lebih stabil, tetapi membutuhkan lebih banyak kuota.</p>
          </div>
        </section>

        <section class="card metrics-card" aria-labelledby="metricsTitle">
          <div class="section-title-row">
            <h2 id="metricsTitle">Ringkasan koneksi</h2>
            <span class="live-label" id="connectionType">Browser</span>
          </div>
          <div class="metric-grid">
            <article class="metric">
              <div class="metric-label">DOWNLOAD</div>
              <div class="metric-value"><span id="downloadValue">—</span><span class="metric-unit">Mbps</span></div>
              <div class="metric-sub">Kecepatan menerima data</div>
            </article>
            <article class="metric">
              <div class="metric-label">UPLOAD</div>
              <div class="metric-value"><span id="uploadValue">—</span><span class="metric-unit">Mbps</span></div>
              <div class="metric-sub">Kecepatan mengirim data</div>
            </article>
            <article class="metric">
              <div class="metric-label">PING</div>
              <div class="metric-value"><span id="pingValue">—</span><span class="metric-unit">ms</span></div>
              <div class="metric-sub">Rata-rata waktu respons</div>
            </article>
            <article class="metric">
              <div class="metric-label">JITTER</div>
              <div class="metric-value"><span id="jitterValue">—</span><span class="metric-unit">ms</span></div>
              <div class="metric-sub">Variasi waktu respons</div>
            </article>
          </div>
          <div class="quality-row">
            <span class="quality-label">Kualitas koneksi</span>
            <span class="quality-value" id="qualityValue">Belum diuji</span>
          </div>
          <div class="quality-track"><div class="quality-fill" id="qualityFill"></div></div>
        </section>
      </div>
    </section>

    <section class="card history-card" aria-labelledby="historyTitle">
      <div class="section-title-row">
        <div>
          <h2 id="historyTitle">Riwayat pengujian</h2>
          <p class="section-caption">Hasil disimpan di browser perangkat ini saja.</p>
        </div>
        <div class="history-actions">
          <button class="quiet-button" id="shareButton" type="button" disabled>Bagikan</button>
          <button class="quiet-button" id="exportButton" type="button" disabled>Ekspor CSV</button>
          <button class="quiet-button" id="clearButton" type="button" disabled>Hapus riwayat</button>
        </div>
      </div>
      <div class="chart-wrap" id="chartWrap" hidden>
        <canvas id="historyChart" aria-label="Grafik perbandingan kecepatan dari riwayat tes"></canvas>
      </div>
      <div class="chart-legend" id="chartLegend" hidden>
        <span class="legend-item"><span class="legend-mark" style="background:var(--mint)"></span>Download</span>
        <span class="legend-item"><span class="legend-mark" style="background:var(--blue)"></span>Upload</span>
      </div>
      <p class="history-empty" id="historyEmpty">Belum ada hasil. Jalankan tes pertama untuk membuat riwayat.</p>
      <ul class="history-list" id="historyList" aria-label="Daftar hasil tes"></ul>
    </section>
    <p class="footer-note">Tes memakai server pengukuran Cloudflare melalui koneksi internet perangkat ini, termasuk Wi-Fi atau jaringan seluler yang sedang digunakan. Lokasi server, kualitas sinyal, perangkat, dan lalu lintas jaringan dapat memengaruhi hasil. Tes upload/download memakai kuota.</p>
  </main>
  <div class="toast" id="toast" role="status" aria-live="polite"></div>

  <script>
    "use strict";

    const STORAGE_KEY = "veloce-speed-history-v2";
    const MAX_HISTORY = 12;
    const TEST_PROFILES = {
      quick: { download: 3, upload: 1 },
      balanced: { download: 10, upload: 5 },
      precise: { download: 20, upload: 10 },
    };
    const GAUGE_MAX_MBPS = 1000;
    const GAUGE_START_ANGLE = -130;
    const GAUGE_END_ANGLE = 130;
    const GAUGE_SWEEP = GAUGE_END_ANGLE - GAUGE_START_ANGLE;
    const elements = {
      button: document.querySelector("#startButton"),
      cancel: document.querySelector("#cancelButton"),
      status: document.querySelector("#testStatus"),
      progress: document.querySelector("#progressFill"),
      progressBar: document.querySelector(".progress-track"),
      gaugeValue: document.querySelector("#gaugeValue"),
      gaugeMode: document.querySelector("#gaugeMode"),
      gaugeCaption: document.querySelector("#gaugeCaption"),
      needle: document.querySelector("#needle"),
      gaugeArc: document.querySelector("#gaugeArc"),
      phases: {
        ping: document.querySelector("#phasePing"),
        download: document.querySelector("#phaseDownload"),
        upload: document.querySelector("#phaseUpload"),
        done: document.querySelector("#phaseDone"),
      },
      ping: document.querySelector("#pingValue"),
      jitter: document.querySelector("#jitterValue"),
      download: document.querySelector("#downloadValue"),
      upload: document.querySelector("#uploadValue"),
      quality: document.querySelector("#qualityValue"),
      qualityFill: document.querySelector("#qualityFill"),
      historyList: document.querySelector("#historyList"),
      historyEmpty: document.querySelector("#historyEmpty"),
      historyCount: document.querySelector("#testCount"),
      export: document.querySelector("#exportButton"),
      clear: document.querySelector("#clearButton"),
      share: document.querySelector("#shareButton"),
      chartWrap: document.querySelector("#chartWrap"),
      chart: document.querySelector("#historyChart"),
      chartLegend: document.querySelector("#chartLegend"),
      connectionDot: document.querySelector("#connectionDot"),
      connectionLabel: document.querySelector("#connectionLabel"),
      connectionType: document.querySelector("#connectionType"),
      toast: document.querySelector("#toast"),
    };
    let history = loadHistory();
    let lastResult = history[0] || null;
    let activeController = null;
    let toastTimer = 0;

    function loadHistory() {
      try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
        if (!Array.isArray(saved)) return [];
        return saved.filter((item) =>
          item &&
          typeof item.date === "string" &&
          Number.isFinite(item.download) &&
          Number.isFinite(item.upload) &&
          Number.isFinite(item.ping) &&
          Number.isFinite(item.jitter)
        ).slice(0, MAX_HISTORY);
      } catch (error) {
        console.warn("Riwayat lokal tidak dapat dibaca.", error);
        return [];
      }
    }

    function persistHistory() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
      } catch (error) {
        console.warn("Riwayat tidak dapat disimpan di browser ini.", error);
        showToast("Penyimpanan lokal browser tidak tersedia.");
      }
    }

    function showToast(message) {
      elements.toast.textContent = message;
      elements.toast.classList.add("visible");
      window.clearTimeout(toastTimer);
      toastTimer = window.setTimeout(() => elements.toast.classList.remove("visible"), 2800);
    }

    function setStatus(message, progress) {
      elements.status.textContent = message;
      elements.progress.style.width = `${progress}%`;
      elements.progressBar.setAttribute("aria-valuenow", String(progress));
    }

    function setPhase(active) {
      for (const [name, element] of Object.entries(elements.phases)) {
        element.classList.toggle("active", name === active);
      }
    }

    function setGauge(speed, mode) {
      const safeSpeed = Number.isFinite(speed) ? Math.max(0, speed) : 0;
      const fraction = Math.min(safeSpeed / GAUGE_MAX_MBPS, 1);
      const angle = GAUGE_START_ANGLE + fraction * GAUGE_SWEEP;
      const dashLength = fraction * 351.9;
      elements.needle.setAttribute("transform", `rotate(${angle} 160 164)`);
      elements.gaugeArc.style.strokeDasharray = `${dashLength} 1000`;
      elements.gaugeValue.textContent = safeSpeed >= 100 ? safeSpeed.toFixed(0) : safeSpeed.toFixed(1);
      elements.gaugeMode.textContent = mode;
      elements.gaugeCaption.textContent = mode === "Siap" ? "Siap mengukur" : `Mengukur ${mode.toLowerCase()}`;
    }

    function buildGaugeTicks() {
      const group = document.querySelector("#gaugeTicks");
      const svgNamespace = "http://www.w3.org/2000/svg";
      for (let index = 0; index <= 20; index += 1) {
        const angle = (GAUGE_START_ANGLE + (GAUGE_SWEEP * index) / 20) * Math.PI / 180;
        const major = index % 4 === 0;
        const innerRadius = major ? 93 : 98;
        const outerRadius = 105;
        const x1 = 160 + Math.cos(angle) * innerRadius;
        const y1 = 164 + Math.sin(angle) * innerRadius;
        const x2 = 160 + Math.cos(angle) * outerRadius;
        const y2 = 164 + Math.sin(angle) * outerRadius;
        const tick = document.createElementNS(svgNamespace, "line");
        tick.setAttribute("x1", x1.toFixed(2));
        tick.setAttribute("y1", y1.toFixed(2));
        tick.setAttribute("x2", x2.toFixed(2));
        tick.setAttribute("y2", y2.toFixed(2));
        tick.setAttribute("class", major ? "gauge-tick major" : "gauge-tick");
        group.append(tick);
        if (major) {
          const label = document.createElementNS(svgNamespace, "text");
          const labelRadius = 77;
          label.setAttribute("x", (160 + Math.cos(angle) * labelRadius).toFixed(2));
          label.setAttribute("y", (164 + Math.sin(angle) * labelRadius + 4).toFixed(2));
          label.setAttribute("class", "gauge-number");
          label.textContent = String(index * (GAUGE_MAX_MBPS / 20));
          group.append(label);
        }
      }
    }

    function getConnectionDescription() {
      const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      if (!connection) return { label: navigator.onLine ? "Terhubung" : "Offline", type: "Browser" };
      const type = connection.type || connection.effectiveType || "Terhubung";
      const downlink = Number.isFinite(connection.downlink) ? ` · ${connection.downlink} Mbps` : "";
      return { label: navigator.onLine ? `${type}${downlink}` : "Offline", type };
    }

    function updateConnectionStatus() {
      const connection = getConnectionDescription();
      elements.connectionLabel.textContent = connection.label;
      elements.connectionType.textContent = connection.type;
      elements.connectionDot.classList.toggle("offline", !navigator.onLine);
    }

    function updateQuality(result) {
      const speedScore = Math.min((result.download / 100) * 65, 65);
      const uploadScore = Math.min((result.upload / 30) * 20, 20);
      const latencyScore = result.ping <= 20 ? 15 : Math.max(0, 15 - (result.ping - 20) / 8);
      const score = Math.round(speedScore + uploadScore + latencyScore);
      let label = "Lambat";
      let color = "var(--red)";
      if (score >= 80) {
        label = "Sangat baik";
        color = "var(--mint)";
      } else if (score >= 55) {
        label = "Baik";
        color = "var(--mint)";
      } else if (score >= 30) {
        label = "Cukup";
        color = "var(--orange)";
      }
      elements.quality.textContent = `${label} · ${score}/100`;
      elements.quality.style.color = color;
      elements.qualityFill.style.width = `${score}%`;
      elements.qualityFill.style.background = color;
    }

    function formatDate(value) {
      return new Intl.DateTimeFormat("id-ID", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(value));
    }

    function makeHistoryCell(label, value, unit) {
      const wrapper = document.createElement("span");
      wrapper.className = "history-number";
      const caption = document.createElement("small");
      caption.textContent = label;
      wrapper.append(caption, document.createTextNode(`${value.toFixed(1)} ${unit}`));
      return wrapper;
    }

    function renderHistory() {
      elements.historyList.replaceChildren();
      elements.historyCount.textContent = String(history.length);
      elements.historyEmpty.hidden = history.length > 0;
      elements.chartWrap.hidden = history.length < 2;
      elements.chartLegend.hidden = history.length < 2;
      elements.export.disabled = history.length === 0;
      elements.clear.disabled = history.length === 0;
      elements.share.disabled = !lastResult;

      history.forEach((result, index) => {
        const row = document.createElement("li");
        row.className = "history-item";
        const date = document.createElement("time");
        date.className = "history-date";
        date.dateTime = result.date;
        date.textContent = formatDate(result.date);
        row.append(
          date,
          makeHistoryCell("DOWNLOAD", result.download, "Mbps"),
          makeHistoryCell("UPLOAD", result.upload, "Mbps"),
          makeHistoryCell("PING", result.ping, "ms")
        );
        const remove = document.createElement("button");
        remove.className = "delete-result";
        remove.type = "button";
        remove.setAttribute("aria-label", `Hapus hasil ${formatDate(result.date)}`);
        remove.textContent = "×";
        remove.addEventListener("click", () => deleteHistoryEntry(index));
        row.append(remove);
        elements.historyList.append(row);
      });
      if (history.length >= 2) drawHistoryChart();
    }

    function drawHistoryChart() {
      const canvas = elements.chart;
      const bounds = canvas.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      const width = Math.max(1, Math.round(bounds.width * ratio));
      const height = Math.max(1, Math.round(bounds.height * ratio));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      const context = canvas.getContext("2d");
      if (!context) return;
      context.clearRect(0, 0, width, height);
      context.save();
      context.scale(ratio, ratio);
      const chartWidth = bounds.width;
      const chartHeight = bounds.height;
      const padding = { top: 12, right: 8, bottom: 24, left: 36 };
      const plotWidth = chartWidth - padding.left - padding.right;
      const plotHeight = chartHeight - padding.top - padding.bottom;
      const recent = [...history].slice(0, 8).reverse();
      const maximum = Math.max(10, ...recent.flatMap((entry) => [entry.download, entry.upload])) * 1.15;
      const styles = getComputedStyle(document.documentElement);
      const gridColor = styles.getPropertyValue("--line").trim();
      const mutedColor = styles.getPropertyValue("--faint").trim();
      const downloadColor = styles.getPropertyValue("--mint").trim();
      const uploadColor = styles.getPropertyValue("--blue").trim();

      context.font = "10px system-ui";
      context.textAlign = "right";
      context.textBaseline = "middle";
      for (let grid = 0; grid <= 3; grid += 1) {
        const y = padding.top + (plotHeight * grid) / 3;
        const value = maximum * (1 - grid / 3);
        context.beginPath();
        context.strokeStyle = gridColor;
        context.lineWidth = 1;
        context.moveTo(padding.left, y);
        context.lineTo(chartWidth - padding.right, y);
        context.stroke();
        context.fillStyle = mutedColor;
        context.fillText(value >= 100 ? value.toFixed(0) : value.toFixed(1), padding.left - 7, y);
      }

      const groupWidth = plotWidth / recent.length;
      const barWidth = Math.min(12, groupWidth * .28);
      recent.forEach((entry, index) => {
        const centerX = padding.left + groupWidth * (index + .5);
        const downloadHeight = (entry.download / maximum) * plotHeight;
        const uploadHeight = (entry.upload / maximum) * plotHeight;
        context.fillStyle = downloadColor;
        context.beginPath();
        context.roundRect(centerX - barWidth - 2, padding.top + plotHeight - downloadHeight, barWidth, downloadHeight, 3);
        context.fill();
        context.fillStyle = uploadColor;
        context.beginPath();
        context.roundRect(centerX + 2, padding.top + plotHeight - uploadHeight, barWidth, uploadHeight, 3);
        context.fill();
        context.fillStyle = mutedColor;
        context.textAlign = "center";
        context.textBaseline = "top";
        context.fillText(String(index + 1), centerX, padding.top + plotHeight + 7);
      });
      context.restore();
    }

    function deleteHistoryEntry(index) {
      history.splice(index, 1);
      lastResult = history[0] || null;
      persistHistory();
      renderHistory();
      showToast("Hasil tes dihapus dari riwayat.");
    }

    function clearHistory() {
      if (!history.length) return;
      if (!window.confirm("Hapus semua riwayat tes dari browser ini?")) return;
      history = [];
      lastResult = null;
      persistHistory();
      renderHistory();
      showToast("Riwayat tes telah dihapus.");
    }

    function exportHistory() {
      if (!history.length) return;
      const header = ["tanggal", "download_mbps", "upload_mbps", "ping_ms", "jitter_ms", "profil"];
      const rows = history.map((item) => [
        item.date,
        item.download,
        item.upload,
        item.ping,
        item.jitter,
        item.profile,
      ]);
      const csv = [header, ...rows].map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\r\n");
      const file = new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(file);
      const link = document.createElement("a");
      link.href = url;
      link.download = `veloce-speed-test-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      showToast("Riwayat berhasil diekspor sebagai CSV.");
    }

    function buildShareText(result) {
      return [
        "Hasil tes kecepatan Veloce",
        `Download: ${result.download.toFixed(1)} Mbps`,
        `Upload: ${result.upload.toFixed(1)} Mbps`,
        `Ping: ${result.ping.toFixed(1)} ms · Jitter: ${result.jitter.toFixed(1)} ms`,
        formatDate(result.date),
        "Diukur ke server Cloudflare melalui koneksi internet perangkat ini.",
      ].join("\n");
    }

    async function shareLatestResult() {
      if (!lastResult) return;
      const text = buildShareText(lastResult);
      if (navigator.share) {
        try {
          await navigator.share({ title: "Hasil tes Veloce", text });
          return;
        } catch (error) {
          if (error instanceof Error && error.name === "AbortError") return;
          console.warn("Berbagi langsung tidak tersedia.", error);
        }
      }
      if (!navigator.clipboard) {
        showToast("Clipboard tidak tersedia pada koneksi ini. Salin hasil dari riwayat.");
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
        showToast("Ringkasan hasil disalin.");
      } catch (error) {
        console.warn("Tidak dapat menyalin hasil.", error);
        showToast("Browser tidak mengizinkan penyalinan otomatis.");
      }
    }

    function randomPayload(size) {
      const payload = new Uint8Array(size);
      for (let offset = 0; offset < size; offset += 65536) {
        crypto.getRandomValues(payload.subarray(offset, Math.min(offset + 65536, size)));
      }
      return payload;
    }

    function calculateJitter(samples) {
      if (samples.length < 2) return 0;
      const differences = samples.slice(1).map((value, index) => Math.abs(value - samples[index]));
      return differences.reduce((sum, value) => sum + value, 0) / differences.length;
    }

    async function measurePing(sampleCount, signal) {
      const samples = [];
      for (let index = 0; index < sampleCount; index += 1) {
        const started = performance.now();
        const response = await fetch(`https://speed.cloudflare.com/__down?bytes=1&sample=${index}&time=${Date.now()}`, {
          cache: "no-store",
          signal,
        });
        if (!response.ok) throw new Error("Gagal mengukur ping ke server tes internet. Periksa koneksi.");
        await response.arrayBuffer();
        samples.push(performance.now() - started);
        setStatus(`Mengukur ping… sampel ${index + 1} dari ${sampleCount}`, 5 + Math.round((index + 1) / sampleCount * 25));
      }
      const average = samples.reduce((sum, value) => sum + value, 0) / samples.length;
      return { ping: average, jitter: calculateJitter(samples) };
    }

    async function measureDownload(sizeMb, signal) {
      const bytesExpected = sizeMb * 1024 * 1024;
      const started = performance.now();
      const response = await fetch(`https://speed.cloudflare.com/__down?bytes=${bytesExpected}&time=${Date.now()}`, {
        cache: "no-store",
        signal,
      });
      if (!response.ok) throw new Error("Download gagal dari server tes internet. Periksa koneksi.");
      const downloaded = await response.arrayBuffer();
      const elapsedSeconds = Math.max((performance.now() - started) / 1000, .001);
      return downloaded.byteLength * 8 / elapsedSeconds / 1_000_000;
    }

    async function measureUpload(sizeMb, signal) {
      const payload = randomPayload(sizeMb * 1024 * 1024);
      const started = performance.now();
      const response = await fetch("https://speed.cloudflare.com/__up", {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: payload,
        signal,
      });
      if (!response.ok) throw new Error("Upload gagal ke server tes internet. Periksa koneksi.");
      await response.arrayBuffer();
      const elapsedSeconds = Math.max((performance.now() - started) / 1000, .001);
      return payload.byteLength * 8 / elapsedSeconds / 1_000_000;
    }

    function displayResult(result) {
      elements.download.textContent = result.download.toFixed(1);
      elements.upload.textContent = result.upload.toFixed(1);
      elements.ping.textContent = result.ping.toFixed(1);
      elements.jitter.textContent = result.jitter.toFixed(1);
      setGauge(result.download, "Download");
      updateQuality(result);
    }

    function resetResult() {
      for (const element of [elements.download, elements.upload, elements.ping, elements.jitter]) {
        element.textContent = "—";
      }
      elements.quality.textContent = "Mengukur…";
      elements.quality.style.color = "";
      elements.qualityFill.style.width = "0";
      setGauge(0, "Siap");
      setPhase("");
    }

    async function runTest() {
      if (activeController) return;
      const profile = TEST_PROFILES[document.querySelector("#testProfile").value] || TEST_PROFILES.balanced;
      const samples = Number(document.querySelector("#pingSamples").value);
      const controller = new AbortController();
      activeController = controller;
      elements.button.disabled = true;
      elements.cancel.disabled = false;
      elements.button.textContent = "Tes sedang berjalan…";
      resetResult();

      try {
        setPhase("ping");
        const latency = await measurePing(samples, controller.signal);

        setPhase("download");
        elements.gaugeMode.textContent = "Download";
        elements.gaugeCaption.textContent = "Mengukur download";
        setStatus(`Mengunduh data uji ${profile.download} MB…`, 35);
        const download = await measureDownload(profile.download, controller.signal);
        elements.download.textContent = download.toFixed(1);
        setGauge(download, "Download");

        setPhase("upload");
        elements.gaugeMode.textContent = "Upload";
        elements.gaugeCaption.textContent = "Mengukur upload";
        setStatus(`Mengunggah data uji ${profile.upload} MB…`, 70);
        const upload = await measureUpload(profile.upload, controller.signal);
        const result = {
          date: new Date().toISOString(),
          download,
          upload,
          ping: latency.ping,
          jitter: latency.jitter,
          profile: document.querySelector("#testProfile").value,
        };
        lastResult = result;
        history = [result, ...history].slice(0, MAX_HISTORY);
        persistHistory();
        displayResult(result);
        renderHistory();
        setPhase("done");
        setStatus("Tes selesai. Hasil tersimpan di riwayat browser ini.", 100);
        showToast("Tes selesai. Hasil koneksi berhasil diperbarui.");
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          setStatus("Tes dibatalkan. Kamu bisa mulai lagi kapan saja.", 0);
          elements.gaugeMode.textContent = "Dibatalkan";
          showToast("Tes dibatalkan.");
        } else {
          console.error("Speed test gagal.", error);
          setStatus(error instanceof Error ? error.message : "Tes gagal. Periksa koneksi ke server.", 0);
          elements.gaugeMode.textContent = "Gagal";
          showToast("Tes gagal. Periksa koneksi dan coba lagi.");
        }
        setPhase("");
      } finally {
        activeController = null;
        elements.cancel.disabled = true;
        elements.button.disabled = false;
        elements.button.textContent = history.length ? "Ulangi tes" : "Mulai tes kecepatan";
      }
    }

    function cancelTest() {
      if (activeController) activeController.abort();
    }

    function toggleTheme() {
      const root = document.documentElement;
      const nextTheme = root.dataset.theme === "light" ? "dark" : "light";
      root.dataset.theme = nextTheme;
      try {
        localStorage.setItem("veloce-speed-theme", nextTheme);
      } catch (error) {
        console.warn("Preferensi tema tidak dapat disimpan.", error);
      }
      window.requestAnimationFrame(drawHistoryChart);
    }

    function restoreTheme() {
      try {
        const saved = localStorage.getItem("veloce-speed-theme");
        const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
        document.documentElement.dataset.theme = saved || (prefersLight ? "light" : "dark");
      } catch (error) {
        console.warn("Preferensi tema tidak dapat dibaca.", error);
      }
    }

    elements.button.addEventListener("click", runTest);
    elements.cancel.addEventListener("click", cancelTest);
    elements.export.addEventListener("click", exportHistory);
    elements.clear.addEventListener("click", clearHistory);
    elements.share.addEventListener("click", shareLatestResult);
    document.querySelector("#themeToggle").addEventListener("click", toggleTheme);
    window.addEventListener("online", updateConnectionStatus);
    window.addEventListener("offline", updateConnectionStatus);
    window.addEventListener("resize", () => {
      if (history.length >= 2) drawHistoryChart();
    });
    if (navigator.connection && navigator.connection.addEventListener) {
      navigator.connection.addEventListener("change", updateConnectionStatus);
    }

    buildGaugeTicks();
    restoreTheme();
    updateConnectionStatus();
    renderHistory();
    if (lastResult) {
      displayResult(lastResult);
      elements.button.textContent = "Ulangi tes";
    }
  </script>
</body>
</html>
"""

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


@app.get("/")
def index() -> Response:
    return Response(PAGE, mimetype="text/html", headers={"Cache-Control": "no-store"})


@app.get("/api/ping")
def ping() -> Response:
    return jsonify(ok=True)


@app.get("/api/download")
def download() -> Response | tuple[Response, int]:
    requested = request.args.get("bytes", default=0, type=int)
    if not 0 < requested <= MAX_DOWNLOAD_BYTES:
        return jsonify(error="Ukuran download harus antara 1 byte dan 25 MiB."), 400

    def generate() -> object:
        remaining = requested
        chunk = b"\0" * min(CHUNK_SIZE, requested)
        while remaining:
            size = min(len(chunk), remaining)
            yield chunk[:size]
            remaining -= size

    response = Response(generate(), mimetype="application/octet-stream")
    response.headers["Content-Length"] = str(requested)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


@app.post("/api/upload")
def upload() -> Response | tuple[Response, int]:
    content_length = request.content_length or 0
    if content_length > MAX_UPLOAD_BYTES:
        return jsonify(error="Ukuran upload melebihi batas 25 MiB."), 413
    if content_length <= 0:
        return jsonify(error="Ukuran upload harus antara 1 byte dan 25 MiB."), 400

    remaining = content_length
    while remaining:
        chunk = request.stream.read(min(CHUNK_SIZE, remaining))
        if not chunk:
            return jsonify(error="Data upload tidak lengkap."), 400
        remaining -= len(chunk)
    return jsonify(ok=True, bytes=content_length)


@app.errorhandler(413)
def request_too_large(_error: Exception) -> tuple[Response, int]:
    return jsonify(error="Ukuran upload melebihi batas 25 MiB."), 413


def main() -> None:
    parser = argparse.ArgumentParser(description="Jalankan website tes kecepatan jaringan.")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Alamat bind (default: 0.0.0.0 untuk menerima koneksi dari semua interface, termasuk LAN).",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port server (default: 8000).")
    parser.add_argument(
        "--public",
        action="store_true",
        help="Buat URL publik sementara menggunakan Cloudflare Tunnel (memerlukan cloudflared).",
    )
    args = parser.parse_args()

    cloudflared = shutil.which("cloudflared") if args.public else None
    if args.public and cloudflared is None:
        parser.error("cloudflared tidak ditemukan. Instal cloudflared lalu jalankan kembali dengan --public.")

    if not 1 <= args.port <= 65535:
        parser.error("Port harus berada di antara 1 dan 65535.")

    print(f"NetSpeed aktif di komputer ini: http://127.0.0.1:{args.port}")
    print(f"Alamat bind server: {args.host}:{args.port}")
    if args.host == "0.0.0.0":
        print("Server menerima koneksi dari jaringan lokal (0.0.0.0).")
    try:
        route_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            route_socket.connect(("192.0.2.1", 80))
            lan_ip = route_socket.getsockname()[0]
            print(f"Di perangkat lain pada Wi-Fi/LAN yang sama, buka: http://{lan_ip}:{args.port}")
        except OSError:
            print("Di perangkat lain pada Wi-Fi/LAN yang sama, buka http://IP-LAN-ANDA:" + str(args.port))
        finally:
            route_socket.close()
    except OSError:
        print("Di perangkat lain pada Wi-Fi/LAN yang sama, buka http://IP-LAN-ANDA:" + str(args.port))

    tunnel_process: subprocess.Popen[str] | None = None
    if args.public:
        print("Membuat tunnel publik sementara. Siapa pun yang memiliki URL tunnel dapat mengakses tes ini.")
        tunnel_process = subprocess.Popen(
            [cloudflared, "tunnel", "--url", f"http://127.0.0.1:{args.port}", "--no-autoupdate"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def relay_tunnel_output() -> None:
            if tunnel_process is None or tunnel_process.stdout is None:
                return
            for line in tunnel_process.stdout:
                match = re.search(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com", line)
                if match:
                    print(f"URL publik: {match.group(0)}", flush=True)
                elif line.strip():
                    print(f"[cloudflared] {line.rstrip()}", flush=True)

        threading.Thread(target=relay_tunnel_output, daemon=True).start()

    print("Hentikan server dengan Ctrl+C.")
    try:
        app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        if tunnel_process is not None:
            tunnel_process.terminate()
            try:
                tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tunnel_process.kill()
                tunnel_process.wait()


if __name__ == "__main__":
    main()