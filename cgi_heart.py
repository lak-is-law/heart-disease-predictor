"""Ultra-high-fidelity 3D CGI Anatomical Heart and Dynamic Cardiac Telemetry Component
Renders an interactive Three.js WebGL anatomical heart with real-time systolic/diastolic
deformation, coronary stenosis visualization, procedural shaders, synchronized Lead-II
ECG oscilloscope, and Web Audio cardiac sound synthesis.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

_CACHED_VENDOR_TAGS: dict[bool, str] = {}


def get_vendor_script_tags(embed: bool = True) -> str:
    """Returns self-contained vendor <script> tags for Three.js and OrbitControls.

    If embed is True and local vendor files exist in portal/vendor, inlines their contents
    directly into the HTML string, enabling 100% offline air-gapped desktop execution.
    Falls back to CDN tags if local vendor files are not present.
    """
    global _CACHED_VENDOR_TAGS
    if embed in _CACHED_VENDOR_TAGS:
        return _CACHED_VENDOR_TAGS[embed]

    base_dir = Path(__file__).resolve().parent
    vendor_dir = base_dir / "portal" / "vendor"
    if not vendor_dir.exists() and hasattr(sys, "_MEIPASS"):
        vendor_dir = Path(sys._MEIPASS) / "portal" / "vendor"

    three_file = vendor_dir / "three.min.js"
    orbit_file = vendor_dir / "OrbitControls.js"

    if embed and three_file.is_file() and orbit_file.is_file():
        three_js = three_file.read_text(encoding="utf-8")
        orbit_js = orbit_file.read_text(encoding="utf-8")
        tags = (
            f"<script>\n/* Inlined three.min.js r128 (Offline Air-Gapped Bundle) */\n{three_js}\n</script>\n"
            f"<script>\n/* Inlined OrbitControls.js r128 (Offline Air-Gapped Bundle) */\n{orbit_js}\n</script>"
        )
    else:
        tags = (
            '<script src="vendor/three.min.js"></script>\n'
            '<script>\n'
            '  if (typeof THREE === "undefined") {\n'
            '    document.write(\'<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\\/script>\');\n'
            '  }\n'
            '</script>\n'
            '<script src="vendor/OrbitControls.js"></script>\n'
            '<script>\n'
            '  if (typeof THREE !== "undefined" && typeof THREE.OrbitControls === "undefined") {\n'
            '    document.write(\'<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"><\\/script>\');\n'
            '  }\n'
            '</script>'
        )

    _CACHED_VENDOR_TAGS[embed] = tags
    return tags


def render_cgi_heart(
    risk_score: float | dict | None = None,
    risk_band: str = "MODERATE",
    bpm: int = 75,
    oldpeak: float = 0.0,
    slope: int = 2,
    ca: int = 0,
    cp: int = 4,
    restecg: int = 0,
    trestbps: int = 120,
    chol: int = 200,
    model_name: str = "Logistic Regression",
    height: int = 680,
    patient_dict: dict | None = None,
    risk_prob: float | None = None,
    embed_vendor: bool = True,
    **kwargs,
) -> str:
    """Generate the complete self-contained HTML/WebGL bundle for Streamlit or web embedding."""

    # --- Robust Parameter Unpacking & Biomarker Extraction Blueprint ---
    def _safe_float(val: object, default: float = 0.0) -> float:
        if val is None:
            return default
        try:
            f = float(val)
            return default if math.isnan(f) or math.isinf(f) else f
        except (ValueError, TypeError):
            return default

    def _safe_int(val: object, default: int = 0) -> int:
        if val is None:
            return default
        try:
            if isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    return default
                return int(val)
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return default

    def _extract_biomarker(
        patient_obj: dict | None,
        key: str,
        fallback: object,
        default: float | int,
        is_float: bool = False,
    ) -> float | int:
        converter = _safe_float if is_float else _safe_int
        if (
            patient_obj is not None
            and isinstance(patient_obj, dict)
            and key in patient_obj
            and patient_obj[key] is not None
        ):
            return converter(patient_obj[key], fallback if fallback is not None else default)
        return converter(fallback if fallback is not None else default, default)

    # 1. Resolve patient dictionary from positional risk_score, patient_dict, or kwargs
    patient = None
    if isinstance(risk_score, dict):
        patient = risk_score
    elif isinstance(patient_dict, dict):
        patient = patient_dict
    elif isinstance(kwargs.get("patient"), dict):
        patient = kwargs.get("patient")
    elif isinstance(kwargs.get("patient_dict"), dict):
        patient = kwargs.get("patient_dict")

    # 2. Resolve score, band, and default_bpm across all calling conventions
    default_bpm = 75
    if isinstance(risk_score, dict):
        # Dictionary passed as first positional argument
        if isinstance(bpm, str) or isinstance(risk_band, (int, float)):
            # 3-arg positional: render_cgi_heart(patient_dict, risk_prob, risk_band)
            # or 2-arg positional: render_cgi_heart(patient_dict, risk_prob)
            score = _safe_float(risk_band, 0.5)
            if isinstance(bpm, str):
                band = bpm.strip()
                default_bpm = _safe_int(kwargs.get("bpm", 75), 75)
            else:
                band = str(kwargs.get("risk_band", "MODERATE"))
                default_bpm = _safe_int(bpm, 75)
        else:
            # Keyword or 2-arg band string: render_cgi_heart(patient_dict, risk_band="HIGH", risk_prob=0.85)
            score = _safe_float(
                risk_prob if risk_prob is not None else kwargs.get("risk_prob", kwargs.get("score", 0.5)),
                0.5,
            )
            band = str(risk_band if risk_band is not None else "MODERATE")
            default_bpm = _safe_int(bpm, 75)
    elif patient is not None:
        # Patient passed via keyword patient_dict=... or patient=...
        score_val = (
            risk_prob
            if risk_prob is not None
            else (
                risk_score
                if risk_score is not None
                else kwargs.get("risk_prob", kwargs.get("score", 0.5))
            )
        )
        score = _safe_float(score_val, 0.5)
        band = str(risk_band if risk_band is not None else "MODERATE")
        default_bpm = _safe_int(bpm, 75)
    else:
        # Standard non-dictionary call: render_cgi_heart(score, band, ...)
        score = _safe_float(
            risk_score if risk_score is not None else (risk_prob if risk_prob is not None else 0.5),
            0.5,
        )
        band = str(risk_band if risk_band is not None else "MODERATE")
        default_bpm = _safe_int(bpm, 75)

    score = max(0.0, min(1.0, score))

    # 3. Resolve biomarkers with robust fallback and None handling
    bpm = _extract_biomarker(patient, "thalach", default_bpm, 75, is_float=False)
    oldpeak = _extract_biomarker(patient, "oldpeak", oldpeak, 0.0, is_float=True)
    slope = _extract_biomarker(patient, "slope", slope, 2, is_float=False)
    ca = _extract_biomarker(patient, "ca", ca, 0, is_float=False)
    cp = _extract_biomarker(patient, "cp", cp, 4, is_float=False)
    restecg = _extract_biomarker(patient, "restecg", restecg, 0, is_float=False)
    trestbps = _extract_biomarker(patient, "trestbps", trestbps, 120, is_float=False)
    chol = _extract_biomarker(patient, "chol", chol, 200, is_float=False)

    # Risk theme colors
    if score < 0.33:
        primary_color = "#34d399"  # Emerald
        glow_color = "#10b981"
        risk_class = "low"
    elif score < 0.66:
        primary_color = "#fbbf24"  # Amber
        glow_color = "#f59e0b"
        risk_class = "mid"
    else:
        primary_color = "#f43f5e"  # Crimson
        glow_color = "#e11d48"
        risk_class = "high"

    # Pre-encode configuration for JavaScript
    config = {
        "risk_score": float(score),
        "risk_band": str(band),
        "bpm": int(bpm),
        "oldpeak": float(oldpeak),
        "slope": int(slope),
        "ca": int(ca),
        "cp": int(cp),
        "restecg": int(restecg),
        "trestbps": int(trestbps),
        "chol": int(chol),
        "model_name": str(model_name),
        "primary_color": primary_color,
        "glow_color": glow_color,
    }
    config_json = json.dumps(config)
    vendor_scripts = get_vendor_script_tags(embed=embed_vendor)

    slope_labels = ["Upsloping", "Flat", "Downsloping"]
    slope_idx = max(0, min(2, slope - 1))
    slope_name = slope_labels[slope_idx]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}

  body, html {{
    width: 100%;
    height: 100%;
    overflow: hidden;
    background-color: #050811;
    font-family: 'Inter', -apple-system, sans-serif;
    color: #e2e8f0;
  }}

  #cgi-container {{
    position: relative;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at 50% 45%, #0d1527 0%, #050811 80%);
  }}

  #webgl-canvas {{
    width: 100%;
    height: 100%;
    display: block;
  }}

  /* Holographic HUD Overlays */
  .hud-top {{
    position: absolute;
    top: 16px;
    left: 20px;
    right: 20px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    pointer-events: none;
    z-index: 10;
  }}

  .hud-badge {{
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(12px);
    border-radius: 8px;
    padding: 8px 14px;
    pointer-events: auto;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }}

  .hud-title {{
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 2px;
  }}

  .hud-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.25rem;
    font-weight: 800;
    color: #ffffff;
  }}

  .hud-pulse-dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: {primary_color};
    box-shadow: 0 0 10px {glow_color};
    margin-right: 6px;
    animation: pulseDot 1s infinite;
  }}

  @keyframes pulseDot {{
    0%, 100% {{ transform: scale(1); opacity: 0.6; }}
    50% {{ transform: scale(1.4); opacity: 1; }}
  }}

  /* Mode Toolbar */
  .mode-toolbar {{
    position: absolute;
    top: 16px;
    right: 20px;
    display: flex;
    gap: 8px;
    pointer-events: auto;
    z-index: 10;
  }}

  .mode-btn {{
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.14);
    color: #94a3b8;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    backdrop-filter: blur(10px);
    transition: all 0.2s ease;
  }}

  .mode-btn:hover {{
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.3);
    background: rgba(30, 41, 59, 0.85);
  }}

  .mode-btn.active {{
    color: #ffffff;
    background: rgba(13, 148, 136, 0.4);
    border-color: #2DD4BF;
    box-shadow: 0 0 12px rgba(45, 212, 191, 0.4);
  }}

  /* Stethoscope Sound Toggle */
  .sound-btn {{
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.14);
    color: #94a3b8;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    backdrop-filter: blur(10px);
    transition: all 0.2s ease;
  }}
  .sound-btn.active {{
    color: #34d399;
    border-color: #34d399;
    background: rgba(52, 211, 153, 0.15);
  }}

  /* Bottom Telemetry HUD with Lead-II ECG Monitor */
  .hud-bottom {{
    position: absolute;
    bottom: 16px;
    left: 20px;
    right: 20px;
    display: flex;
    gap: 16px;
    align-items: flex-end;
    pointer-events: none;
    z-index: 10;
  }}

  .ecg-card {{
    flex: 1;
    background: rgba(10, 15, 29, 0.82);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 12px 16px;
    backdrop-filter: blur(14px);
    pointer-events: auto;
    box-shadow: 0 6px 24px rgba(0,0,0,0.5);
  }}

  .ecg-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }}

  .ecg-title {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .ecg-meta {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #94a3b8;
  }}

  #ecg-canvas {{
    width: 100%;
    height: 70px;
    display: block;
    background: #070C18;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }}

  /* Vitals Pill HUD */
  .vitals-grid {{
    display: flex;
    gap: 10px;
    pointer-events: auto;
  }}

  .vitals-pill {{
    background: rgba(10, 15, 29, 0.82);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 10px 14px;
    backdrop-filter: blur(14px);
    min-width: 110px;
  }}

  .vitals-pill-label {{
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
    margin-bottom: 2px;
  }}

  .vitals-pill-val {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    font-weight: 800;
    color: #ffffff;
  }}

  /* Interactive Navigation Hint */
  .orbit-hint {{
    position: absolute;
    bottom: 120px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 4px 14px;
    border-radius: 999px;
    font-size: 0.7rem;
    color: #94a3b8;
    pointer-events: none;
    letter-spacing: 0.05em;
  }}

  @media (max-width: 640px) {{
    .hud-top {{
      flex-direction: column;
      align-items: stretch;
      left: 12px;
      right: 12px;
      top: 12px;
      gap: 8px;
    }}
    .mode-toolbar {{
      position: static;
      width: 100%;
      overflow-x: auto;
      padding-bottom: 4px;
      display: flex;
      gap: 6px;
      -webkit-overflow-scrolling: touch;
    }}
    .mode-btn, .sound-btn {{
      min-height: 40px;
      padding: 6px 10px;
      font-size: 0.72rem;
      white-space: nowrap;
    }}
    .hud-bottom {{
      flex-direction: column;
      left: 12px;
      right: 12px;
      bottom: 12px;
      gap: 8px;
    }}
    .ecg-card {{
      width: 100%;
      padding: 8px 12px;
    }}
    .vitals-grid {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      gap: 6px;
    }}
    .vitals-pill {{
      flex: 1;
      min-width: 0;
      padding: 8px 10px;
    }}
  }}
</style>
{vendor_scripts}
</head>
<body>

<div id="cgi-container">
  <!-- Top HUD -->
  <div class="hud-top">
    <div class="hud-badge">
      <div class="hud-title">
        <span class="hud-pulse-dot"></span>Cardiac Telemetry & AI Diagnosis
      </div>
      <div class="hud-value" style="color: {primary_color};">
        {band} ({int(score * 100)}%)
      </div>
      <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 2px;">
        Model: <strong>{model_name}</strong>
      </div>
    </div>

    <!-- Mode Switcher -->
    <div class="mode-toolbar">
      <button class="mode-btn active" onclick="setMode('cta')">Anatomical CTA</button>
      <button class="mode-btn" onclick="setMode('perfusion')">Perfusion Map</button>
      <button class="mode-btn" onclick="setMode('fluoro')">Fluoroscopy</button>
      <button class="mode-btn" onclick="setMode('ffr')">Coronary FFR</button>
      <button class="sound-btn" id="sound-btn" onclick="toggleCardiacAudio()">
        <span id="sound-icon">[Muted]</span> Sound
      </button>
    </div>
  </div>

  <!-- Orbit Hint -->
  <div class="orbit-hint">
    Click & Drag to Rotate 360° · Scroll to Zoom · Right Click to Pan
  </div>

  <!-- Bottom Telemetry HUD -->
  <div class="hud-bottom">
    <!-- Live Vector ECG -->
    <div class="ecg-card">
      <div class="ecg-header">
        <div class="ecg-title">
          <span style="color:{primary_color}; font-weight:800;">LEAD II</span>
          <span>· Real-time Vector Cardiogram (25 mm/s · 10 mm/mV)</span>
        </div>
        <div class="ecg-meta">
          ST Dep: <strong style="color:{primary_color};">{oldpeak:.1f} mm</strong> | Slope: <strong>{slope_name}</strong>
        </div>
      </div>
      <canvas id="ecg-canvas"></canvas>
    </div>

    <!-- Vitals HUD -->
    <div class="vitals-grid">
      <div class="vitals-pill">
        <div class="vitals-pill-label">Heart Rate</div>
        <div class="vitals-pill-val" style="color: {primary_color};">
          <span id="live-bpm">{bpm}</span> <span style="font-size:0.75rem; color:#94a3b8;">BPM</span>
        </div>
      </div>
      <div class="vitals-pill">
        <div class="vitals-pill-label">Stenosis (Vessels)</div>
        <div class="vitals-pill-val" style="color: {primary_color if ca > 0 else '#34d399'};">
          {ca} / 3 <span style="font-size:0.75rem; color:#94a3b8;">Occluded</span>
        </div>
      </div>
      <div class="vitals-pill">
        <div class="vitals-pill-label">Blood Pressure</div>
        <div class="vitals-pill-val">
          {trestbps} <span style="font-size:0.75rem; color:#94a3b8;">mmHg</span>
        </div>
      </div>
    </div>
  </div>

  <canvas id="webgl-canvas"></canvas>
</div>

<script>
// ==============================================================================
// 3D CGI ANATOMICAL HEART ENGINE (THREE.JS + PROCEDURAL SHADERS)
// ==============================================================================
const CONFIG = {config_json};

let scene, camera, renderer, controls;
let heartGroup;
let lvMesh, rvMesh, laMesh, raMesh, laaMesh, raaMesh;
let aortaMesh, pulmonaryMesh, rpaMesh, lpaMesh, svcMesh, ivcMesh;
let pulmonaryVeins = [], supraAorticBranches = [], coronaryVessels = [];
let stenosisMarkers = [], stenosisBeacons = [], conductionFibers = [];
let particleSystem;
let currentMode = 'cta';
let animationTime = 0;
let clock = new THREE.Clock();
let isCgiContextLost = false;
let cgiAnimationId = null;

// Audio Synth Context
let audioCtx = null;
let soundEnabled = false;
let nextBeatTime = 0;

// ECG State
let ecgCanvas, ecgCtx;
let sweepX = 0;
let ecgLastY = 0;
const pxPerMm = 3.78;
const speedMmPerSec = 25.0;
const voltageScaleMmPerMv = 10.0;

// Procedural in-memory myocardial myofibril bump map (0 KB disk footprint)
let _cgiMyocardialBumpTex = null;
function createMyocardialBumpMap() {{
  if (_cgiMyocardialBumpTex) return _cgiMyocardialBumpTex;
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#808080';
  ctx.fillRect(0, 0, 256, 256);
  ctx.lineWidth = 1.5;
  for (let y = 0; y < 256; y += 3) {{
    const val = Math.floor(128 + 48 * Math.sin(y * 0.35 + Math.sin(y * 0.08) * 3.0));
    ctx.strokeStyle = `rgb(${{val}},${{val}},${{val}})`;
    ctx.beginPath();
    ctx.moveTo(0, y);
    for (let x = 0; x <= 256; x += 16) {{
      const dy = Math.sin(x * 0.05 + y * 0.1) * 3.0;
      ctx.lineTo(x, y + dy);
    }}
    ctx.stroke();
  }}
  _cgiMyocardialBumpTex = new THREE.CanvasTexture(canvas);
  _cgiMyocardialBumpTex.wrapS = THREE.RepeatWrapping;
  _cgiMyocardialBumpTex.wrapT = THREE.RepeatWrapping;
  _cgiMyocardialBumpTex.repeat.set(4, 8);
  return _cgiMyocardialBumpTex;
}}

/**
 * AHA 17-Segment Partitioning
 */
function getAHASegment(x, y, z) {{
  if (y < -0.85) return 17; // Apex
  const theta = Math.atan2(z, x);

  if (y >= 0.25) {{
    if (theta >= Math.PI / 6 && theta < Math.PI / 2) return 1;
    if (theta >= Math.PI / 2 && theta < (5 * Math.PI) / 6) return 2;
    if (theta >= (5 * Math.PI) / 6 || theta < (-5 * Math.PI) / 6) return 3;
    if (theta >= (-5 * Math.PI) / 6 && theta < -Math.PI / 2) return 4;
    if (theta >= -Math.PI / 2 && theta < -Math.PI / 6) return 5;
    return 6;
  }}

  if (y >= -0.35) {{
    if (theta >= Math.PI / 6 && theta < Math.PI / 2) return 7;
    if (theta >= Math.PI / 2 && theta < (5 * Math.PI) / 6) return 8;
    if (theta >= (5 * Math.PI) / 6 || theta < (-5 * Math.PI) / 6) return 9;
    if (theta >= (-5 * Math.PI) / 6 && theta < -Math.PI / 2) return 10;
    if (theta >= -Math.PI / 2 && theta < -Math.PI / 6) return 11;
    return 12;
  }}

  if (theta >= 0 && theta < Math.PI / 2) return 13;
  if (theta >= Math.PI / 2 && theta <= Math.PI) return 14;
  if (theta >= -Math.PI && theta < -Math.PI / 2) return 15;
  return 16;
}}

function applyAHAPerfusionColors(geometry) {{
  if (!geometry || !geometry.attributes.position) return;
  const pos = geometry.attributes.position;
  const count = pos.count;
  const colors = new Float32Array(count * 3);

  const COLOR_NORMAL = new THREE.Color(0x059669);
  const COLOR_REVERSIBLE = new THREE.Color(0xD97706);
  const COLOR_INFARCT = new THREE.Color(0x991B1B);

  const ladInfarct = CONFIG.ca >= 1 && (CONFIG.oldpeak >= 2.5);
  const ladIschemia = CONFIG.ca >= 1 || CONFIG.oldpeak >= 1.2 || CONFIG.risk_score >= 0.45;

  const rcaInfarct = CONFIG.ca >= 2 && (CONFIG.oldpeak >= 3.0);
  const rcaIschemia = CONFIG.ca >= 2 || CONFIG.oldpeak >= 2.0;

  const lcxInfarct = CONFIG.ca >= 3 && CONFIG.oldpeak >= 3.5;
  const lcxIschemia = CONFIG.ca >= 3 || CONFIG.risk_score >= 0.75;

  const ladColor = ladInfarct ? COLOR_INFARCT : (ladIschemia ? COLOR_REVERSIBLE : COLOR_NORMAL);
  const rcaColor = rcaInfarct ? COLOR_INFARCT : (rcaIschemia ? COLOR_REVERSIBLE : COLOR_NORMAL);
  const lcxColor = lcxInfarct ? COLOR_INFARCT : (lcxIschemia ? COLOR_REVERSIBLE : COLOR_NORMAL);

  for (let i = 0; i < count; i++) {{
    const seg = getAHASegment(pos.getX(i), pos.getY(i), pos.getZ(i));
    let c = COLOR_NORMAL;
    if ([1, 2, 7, 8, 13, 14, 17].includes(seg)) c = ladColor;
    else if ([3, 4, 9, 10, 15].includes(seg)) c = rcaColor;
    else if ([5, 6, 11, 12, 16].includes(seg)) c = lcxColor;

    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  }}
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geometry.attributes.color.needsUpdate = true;
}}

function getFFRColor(val) {{
  if (val >= 0.85) return new THREE.Color(0x10B981);
  if (val >= 0.80) return new THREE.Color(0xFBBF24);
  if (val >= 0.75) return new THREE.Color(0xF97316);
  return new THREE.Color(0xEF4444);
}}

function applyFFRGradient(tubeGeo, isStenosed, distalFFR) {{
  if (!tubeGeo || !tubeGeo.attributes.position) return;
  const count = tubeGeo.attributes.position.count;
  const radialSegments = (tubeGeo.parameters && tubeGeo.parameters.radialSegments) ? (tubeGeo.parameters.radialSegments + 1) : 17;
  const tubularSegments = (tubeGeo.parameters && tubeGeo.parameters.tubularSegments) ? tubeGeo.parameters.tubularSegments : 40;
  const colors = new Float32Array(count * 3);

  for (let i = 0; i < count; i++) {{
    const t = Math.min(1.0, Math.floor(i / radialSegments) / tubularSegments);
    let ffrAtPoint;

    if (!isStenosed) {{
      ffrAtPoint = 0.98 - 0.04 * t;
    }} else {{
      if (t <= 0.30) {{
        ffrAtPoint = 0.98 - 0.04 * (t / 0.30);
      }} else if (t <= 0.50) {{
        const lesionProgress = (t - 0.30) / 0.20;
        ffrAtPoint = 0.94 - (0.94 - distalFFR) * lesionProgress;
      }} else {{
        ffrAtPoint = distalFFR - 0.02 * (t - 0.50);
      }}
    }}

    const c = getFFRColor(ffrAtPoint);
    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  }}
  tubeGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  tubeGeo.attributes.color.needsUpdate = true;
}}

init3D();
initECG();
animate();

function init3D() {{
  const container = document.getElementById('cgi-container');
  const canvas = document.getElementById('webgl-canvas');
  if (!container || !canvas || typeof THREE === 'undefined') return;

  // WebGL Context Loss Handlers
  if (!canvas._hasContextLoss) {{
    canvas._hasContextLoss = true;
    canvas.addEventListener('webglcontextlost', (e) => {{
      e.preventDefault();
      isCgiContextLost = true;
      if (cgiAnimationId) {{
        cancelAnimationFrame(cgiAnimationId);
        cgiAnimationId = null;
      }}
      const hint = document.querySelector('.orbit-hint');
      if (hint) hint.innerText = '[GPU Context Lost] Restoring 3D telemetry...';
    }}, false);

    canvas.addEventListener('webglcontextrestored', () => {{
      isCgiContextLost = false;
      teardownCgiScene();
      init3D();
      setMode(currentMode);
      animate();
      const hint = document.querySelector('.orbit-hint');
      if (hint) hint.innerText = 'Click & Drag to Rotate 360° · Scroll to Zoom · Right Click to Pan';
    }}, false);
  }}

  // Scene
  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x050811, 0.038);

  // Camera
  camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
  camera.position.set(0, 0.8, 5.2);

  // Renderer (DPR Clamped to <= 2.0 to enforce <120MB VRAM budget)
  renderer = new THREE.WebGLRenderer({{
    canvas: canvas,
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance'
  }});
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.30;

  // OrbitControls
  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.minDistance = 2.5;
  controls.maxDistance = 8.5;
  controls.maxPolarAngle = Math.PI / 1.75;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.8;

  setupLighting();

  heartGroup = new THREE.Group();
  scene.add(heartGroup);

  buildAnatomy();
  buildCoronaryTree();
  buildConductionSystem();
  buildParticleField();

  window.removeEventListener('resize', onWindowResize);
  window.addEventListener('resize', onWindowResize);
}}

function teardownCgiScene() {{
  if (scene) {{
    scene.traverse(obj => {{
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {{
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
        else obj.material.dispose();
      }}
    }});
  }}
  if (renderer) {{
    renderer.dispose();
    renderer = null;
  }}
  coronaryVessels = [];
  stenosisMarkers = [];
  stenosisBeacons = [];
  conductionFibers = [];
  pulmonaryVeins = [];
  supraAorticBranches = [];
  window.removeEventListener('resize', onWindowResize);
}}

function setupLighting() {{
  const ambientLight = new THREE.AmbientLight(0x1e293b, 1.4);
  scene.add(ambientLight);

  const mainLight = new THREE.DirectionalLight(0xffffff, 2.2);
  mainLight.position.set(5, 8, 6);
  scene.add(mainLight);

  const rimLight = new THREE.DirectionalLight(new THREE.Color(CONFIG.primary_color), 2.2);
  rimLight.position.set(-6, -3, -5);
  scene.add(rimLight);

  const topGlow = new THREE.PointLight(new THREE.Color(CONFIG.glow_color), 1.8, 10);
  topGlow.position.set(0, 3, 2);
  scene.add(topGlow);
}}

/**
 * 1. Procedural 4-Chamber Cardiac Geometry & Great Vessels
 */
function buildAnatomy() {{
  // A. LEFT VENTRICLE (LV) - Conical wringing apex, 45° tilt
  const lvGeo = new THREE.SphereGeometry(1.15, 48, 48);
  const lvPos = lvGeo.attributes.position;
  for (let i = 0; i < lvPos.count; i++) {{
    let x = lvPos.getX(i);
    let y = lvPos.getY(i);
    let z = lvPos.getZ(i);

    if (y < 0) {{
      const taper = 1.0 + y * 0.48;
      x *= Math.max(0.20, taper);
      z *= Math.max(0.22, taper);
      x -= y * 0.26; // 42° - 45° apex tilt
      z += y * 0.08;
    }} else {{
      x *= 1.05;
      z *= 0.96;
    }}

    // Anterior interventricular sulcus (LAD bed)
    if (z > 0 && x > -0.35 && x < 0.15) {{
      z -= Math.max(0, 0.09 * (1.0 - Math.abs(x + 0.10) / 0.25));
    }}
    // Posterior interventricular sulcus (PDA bed)
    if (z < 0 && x > -0.25 && x < 0.20) {{
      z += Math.max(0, 0.07 * (1.0 - Math.abs(x) / 0.22));
    }}
    lvPos.setXYZ(i, x, y, z);
  }}
  lvGeo.computeVertexNormals();
  lvMesh = new THREE.Mesh(lvGeo, getMaterial('lv'));
  heartGroup.add(lvMesh);

  // B. RIGHT VENTRICLE (RV) - Crescentic pouch wrapped anteriorly around septum
  const rvCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.05, 0.45, 0.55),
    new THREE.Vector3(0.42, 0.30, 0.62),
    new THREE.Vector3(0.68, 0.00, 0.50),
    new THREE.Vector3(0.72, -0.35, 0.32),
    new THREE.Vector3(0.48, -0.65, 0.20),
    new THREE.Vector3(0.12, -0.78, 0.15)
  ]);
  const rvGeo = new THREE.TubeGeometry(rvCurve, 32, 0.28, 18, false);
  const rvPos = rvGeo.attributes.position;
  for (let i = 0; i < rvPos.count; i++) {{
    let x = rvPos.getX(i);
    if (x < 0.15) x = 0.15 + (x - 0.15) * 0.45;
    rvPos.setXYZ(i, x, rvPos.getY(i), rvPos.getZ(i));
  }}
  rvGeo.computeVertexNormals();
  rvMesh = new THREE.Mesh(rvGeo, getMaterial('rv'));
  heartGroup.add(rvMesh);

  // C. LEFT ATRIUM (LA), LAA & 4 PULMONARY VEINS
  const laGeo = new THREE.SphereGeometry(0.60, 32, 32);
  laMesh = new THREE.Mesh(laGeo, getMaterial('la'));
  laMesh.scale.set(1.15, 0.85, 0.95);
  laMesh.position.set(-0.24, 0.92, -0.38);
  heartGroup.add(laMesh);

  // LAA auricle
  const laaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.48, 0.95, -0.15),
    new THREE.Vector3(-0.62, 0.85, 0.12),
    new THREE.Vector3(-0.52, 0.72, 0.35),
    new THREE.Vector3(-0.38, 0.62, 0.40)
  ]);
  laaMesh = new THREE.Mesh(new THREE.TubeGeometry(laaCurve, 20, 0.085, 12, false), getMaterial('la'));
  heartGroup.add(laaMesh);

  // 4 Pulmonary Veins (LSPV, LIPV, RSPV, RIPV)
  pulmonaryVeins = [];
  [
    {{ s: [-0.48, 1.08, -0.42], e: [-0.80, 1.25, -0.62], r: 0.075 }},
    {{ s: [-0.48, 0.80, -0.45], e: [-0.80, 0.68, -0.68], r: 0.070 }},
    {{ s: [0.10, 1.10, -0.45],  e: [0.42, 1.28, -0.68],  r: 0.075 }},
    {{ s: [0.10, 0.78, -0.48],  e: [0.42, 0.65, -0.70],  r: 0.070 }}
  ].forEach(pv => {{
    const c = new THREE.CatmullRomCurve3([new THREE.Vector3(...pv.s), new THREE.Vector3(...pv.e)]);
    const m = new THREE.Mesh(new THREE.TubeGeometry(c, 12, pv.r, 12, false), getMaterial('pulmonary'));
    heartGroup.add(m);
    pulmonaryVeins.push(m);
  }});

  // D. RIGHT ATRIUM (RA), RAA, SVC & IVC
  const raGeo = new THREE.SphereGeometry(0.58, 32, 32);
  raMesh = new THREE.Mesh(raGeo, getMaterial('ra'));
  raMesh.scale.set(1.05, 0.90, 0.95);
  raMesh.position.set(0.54, 0.84, 0.05);
  heartGroup.add(raMesh);

  // RAA auricle
  const raaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.42, 0.96, 0.22),
    new THREE.Vector3(0.28, 0.90, 0.40),
    new THREE.Vector3(0.12, 0.84, 0.46)
  ]);
  raaMesh = new THREE.Mesh(new THREE.TubeGeometry(raaCurve, 16, 0.095, 12, false), getMaterial('ra'));
  heartGroup.add(raaMesh);

  // SVC & IVC
  const svcCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.60, 0.95, -0.18),
    new THREE.Vector3(0.62, 1.45, -0.22),
    new THREE.Vector3(0.62, 1.95, -0.22)
  ]);
  svcMesh = new THREE.Mesh(new THREE.TubeGeometry(svcCurve, 20, 0.16, 16, false), getMaterial('pulmonary'));
  heartGroup.add(svcMesh);

  const ivcCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.56, 0.55, -0.24),
    new THREE.Vector3(0.56, 0.10, -0.26),
    new THREE.Vector3(0.54, -0.42, -0.28)
  ]);
  ivcMesh = new THREE.Mesh(new THREE.TubeGeometry(ivcCurve, 18, 0.17, 16, false), getMaterial('pulmonary'));
  heartGroup.add(ivcMesh);

  // E. ASCENDING AORTA, ARCH & 3 SUPRA-AORTIC TRUNKS
  const aortaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.04, 0.62, 0.14),
    new THREE.Vector3(0.16, 1.15, 0.14),
    new THREE.Vector3(0.18, 1.52, 0.04),
    new THREE.Vector3(0.05, 1.92, -0.12),
    new THREE.Vector3(-0.24, 1.88, -0.28),
    new THREE.Vector3(-0.46, 1.62, -0.40),
    new THREE.Vector3(-0.54, 0.82, -0.48),
    new THREE.Vector3(-0.56, 0.12, -0.52)
  ]);
  aortaMesh = new THREE.Mesh(new THREE.TubeGeometry(aortaCurve, 48, 0.22, 22, false), getMaterial('aorta'));
  heartGroup.add(aortaMesh);

  // 3 Supra-Aortic Trunks: Brachiocephalic, Left Common Carotid, Left Subclavian
  supraAorticBranches = [];
  [
    {{ s: [0.10, 1.88, -0.06],  e: [0.24, 2.55, 0.02],   r: 0.075, name: 'Brachiocephalic' }},
    {{ s: [-0.06, 1.92, -0.16], e: [-0.10, 2.60, -0.12], r: 0.062, name: 'Left Common Carotid' }},
    {{ s: [-0.24, 1.86, -0.26], e: [-0.40, 2.55, -0.30], r: 0.060, name: 'Left Subclavian' }}
  ].forEach(b => {{
    const c = new THREE.CatmullRomCurve3([new THREE.Vector3(...b.s), new THREE.Vector3(...b.e)]);
    const m = new THREE.Mesh(new THREE.TubeGeometry(c, 16, b.r, 14, false), getMaterial('aorta'));
    heartGroup.add(m);
    supraAorticBranches.push(m);
  }});

  // F. MAIN PULMONARY ARTERY & BIFURCATION (RPA / LPA)
  const mpaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.12, 0.55, 0.40),
    new THREE.Vector3(-0.18, 1.05, 0.28),
    new THREE.Vector3(-0.26, 1.45, 0.10),
    new THREE.Vector3(-0.32, 1.65, -0.05)
  ]);
  pulmonaryMesh = new THREE.Mesh(new THREE.TubeGeometry(mpaCurve, 28, 0.20, 18, false), getMaterial('pulmonary'));
  heartGroup.add(pulmonaryMesh);

  const rpaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.32, 1.65, -0.05),
    new THREE.Vector3(-0.05, 1.58, -0.18),
    new THREE.Vector3(0.28, 1.50, -0.26),
    new THREE.Vector3(0.65, 1.42, -0.30)
  ]);
  rpaMesh = new THREE.Mesh(new THREE.TubeGeometry(rpaCurve, 24, 0.145, 16, false), getMaterial('pulmonary'));
  heartGroup.add(rpaMesh);

  const lpaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.32, 1.65, -0.05),
    new THREE.Vector3(-0.52, 1.58, -0.14),
    new THREE.Vector3(-0.78, 1.50, -0.22)
  ]);
  lpaMesh = new THREE.Mesh(new THREE.TubeGeometry(lpaCurve, 20, 0.140, 16, false), getMaterial('pulmonary'));
  heartGroup.add(lpaMesh);
}}

/**
 * 2. Anatomical Coronary Tree with Tangent Quaternion Stenosis Rings
 */
function buildCoronaryTree() {{
  coronaryVessels = [];

  // LMCA
  const lmcaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.04, 0.70, 0.20),
    new THREE.Vector3(-0.10, 0.68, 0.35),
    new THREE.Vector3(-0.16, 0.66, 0.48)
  ]);
  const lmcaMesh = new THREE.Mesh(new THREE.TubeGeometry(lmcaCurve, 12, 0.050, 14, false), getMaterial('coronary'));
  heartGroup.add(lmcaMesh);
  coronaryVessels.push(lmcaMesh);

  // LAD
  const ladCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.16, 0.66, 0.48),
    new THREE.Vector3(-0.18, 0.38, 0.78),
    new THREE.Vector3(-0.21, 0.08, 0.93),
    new THREE.Vector3(-0.28, -0.32, 0.88),
    new THREE.Vector3(-0.36, -0.75, 0.68),
    new THREE.Vector3(-0.44, -1.15, 0.32),
    new THREE.Vector3(-0.42, -1.25, 0.10)
  ]);
  const ladMesh = new THREE.Mesh(new THREE.TubeGeometry(ladCurve, 48, 0.044, 16, false), getMaterial('coronary'));
  heartGroup.add(ladMesh);
  coronaryVessels.push(ladMesh);

  // D1
  const d1Curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.19, 0.24, 0.86),
    new THREE.Vector3(-0.36, 0.05, 0.82),
    new THREE.Vector3(-0.52, -0.22, 0.68),
    new THREE.Vector3(-0.60, -0.52, 0.48)
  ]);
  const d1Mesh = new THREE.Mesh(new THREE.TubeGeometry(d1Curve, 24, 0.030, 12, false), getMaterial('coronary'));
  heartGroup.add(d1Mesh);
  coronaryVessels.push(d1Mesh);

  // LCx
  const lcxCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.16, 0.66, 0.48),
    new THREE.Vector3(-0.38, 0.64, 0.42),
    new THREE.Vector3(-0.62, 0.54, 0.25),
    new THREE.Vector3(-0.78, 0.35, -0.02),
    new THREE.Vector3(-0.80, 0.05, -0.22),
    new THREE.Vector3(-0.68, -0.22, -0.38)
  ]);
  const lcxMesh = new THREE.Mesh(new THREE.TubeGeometry(lcxCurve, 36, 0.038, 14, false), getMaterial('coronary'));
  heartGroup.add(lcxMesh);
  coronaryVessels.push(lcxMesh);

  // OM1
  const om1Curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.78, 0.35, -0.02),
    new THREE.Vector3(-0.82, 0.04, 0.12),
    new THREE.Vector3(-0.78, -0.36, 0.18),
    new THREE.Vector3(-0.68, -0.70, 0.12)
  ]);
  const om1Mesh = new THREE.Mesh(new THREE.TubeGeometry(om1Curve, 24, 0.028, 12, false), getMaterial('coronary'));
  heartGroup.add(om1Mesh);
  coronaryVessels.push(om1Mesh);

  // RCA
  const rcaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.18, 0.68, 0.24),
    new THREE.Vector3(0.45, 0.60, 0.38),
    new THREE.Vector3(0.72, 0.42, 0.48),
    new THREE.Vector3(0.84, 0.08, 0.42),
    new THREE.Vector3(0.80, -0.32, 0.32),
    new THREE.Vector3(0.62, -0.62, 0.12),
    new THREE.Vector3(0.32, -0.78, -0.15)
  ]);
  const rcaMesh = new THREE.Mesh(new THREE.TubeGeometry(rcaCurve, 48, 0.042, 16, false), getMaterial('coronary'));
  heartGroup.add(rcaMesh);
  coronaryVessels.push(rcaMesh);

  // AM
  const amCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.84, 0.08, 0.42),
    new THREE.Vector3(0.76, -0.25, 0.50),
    new THREE.Vector3(0.55, -0.58, 0.45),
    new THREE.Vector3(0.28, -0.75, 0.38)
  ]);
  const amMesh = new THREE.Mesh(new THREE.TubeGeometry(amCurve, 24, 0.026, 12, false), getMaterial('coronary'));
  heartGroup.add(amMesh);
  coronaryVessels.push(amMesh);

  // PDA
  const pdaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.32, -0.78, -0.15),
    new THREE.Vector3(0.12, -0.92, -0.05),
    new THREE.Vector3(-0.12, -1.08, 0.08),
    new THREE.Vector3(-0.32, -1.20, 0.15)
  ]);
  const pdaMesh = new THREE.Mesh(new THREE.TubeGeometry(pdaCurve, 28, 0.030, 12, false), getMaterial('coronary'));
  heartGroup.add(pdaMesh);
  coronaryVessels.push(pdaMesh);

  // Dynamic Stenosis Rings governed by CONFIG.ca
  stenosisMarkers = [];
  stenosisBeacons = [];

  const lesionDefs = [
    {{ name: 'Mid LAD Stenosis', curve: ladCurve, t: 0.32 }},
    {{ name: 'Mid RCA Stenosis', curve: rcaCurve, t: 0.38 }},
    {{ name: 'Proximal LCx Stenosis', curve: lcxCurve, t: 0.25 }}
  ];

  const activeLesions = Math.min(CONFIG.ca || 0, lesionDefs.length);

  for (let i = 0; i < activeLesions; i++) {{
    const def = lesionDefs[i];
    const pt = def.curve.getPoint(def.t);
    const tangent = def.curve.getTangent(def.t).normalize();
    const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), tangent);

    // Atheromatous Plaque Collar
    const plaqueGeo = new THREE.TorusGeometry(0.068, 0.022, 16, 32);
    const plaqueMat = new THREE.MeshStandardMaterial({{
      color: 0xEF4444,
      emissive: 0xDC2626,
      emissiveIntensity: 1.0,
      roughness: 0.3,
      metalness: 0.2
    }});
    const plaqueMesh = new THREE.Mesh(plaqueGeo, plaqueMat);
    plaqueMesh.position.copy(pt);
    plaqueMesh.quaternion.copy(quaternion);
    heartGroup.add(plaqueMesh);
    stenosisMarkers.push(plaqueMesh);

    // Osteoid Calcification Ring
    const calcGeo = new THREE.TorusGeometry(0.088, 0.012, 14, 28);
    const calcMat = new THREE.MeshStandardMaterial({{
      color: 0xF8FAFC,
      roughness: 0.15,
      metalness: 0.85
    }});
    const calcMesh = new THREE.Mesh(calcGeo, calcMat);
    calcMesh.position.copy(pt);
    calcMesh.quaternion.copy(quaternion);
    heartGroup.add(calcMesh);
    stenosisMarkers.push(calcMesh);

    // Ischemic Warning Beacon
    const beacon = new THREE.PointLight(0xFF0044, 2.8, 1.4);
    beacon.position.copy(pt);
    heartGroup.add(beacon);
    stenosisBeacons.push(beacon);
  }}
}}

function buildConductionSystem() {{
  const fiberPaths = [
    [new THREE.Vector3(0.5, 1.1, -0.1), new THREE.Vector3(0.1, 0.8, 0.2)],
    [new THREE.Vector3(0.1, 0.8, 0.2), new THREE.Vector3(0.0, 0.3, 0.4)],
    [new THREE.Vector3(0.0, 0.3, 0.4), new THREE.Vector3(-0.35, -0.9, 0.3)],
    [new THREE.Vector3(0.0, 0.3, 0.4), new THREE.Vector3(0.45, -0.7, 0.2)],
  ];

  fiberPaths.forEach(pts => {{
    const curve = new THREE.CatmullRomCurve3(pts);
    const geo = new THREE.TubeGeometry(curve, 20, 0.02, 8, false);
    const mat = new THREE.MeshBasicMaterial({{
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.0,
      wireframe: true
    }});
    const mesh = new THREE.Mesh(geo, mat);
    heartGroup.add(mesh);
    conductionFibers.push(mesh);
  }});
}}

function buildParticleField() {{
  const count = 450;
  const geo = new THREE.BufferGeometry();
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const baseCol = new THREE.Color(CONFIG.primary_color);

  for (let i = 0; i < count; i++) {{
    const r = 1.8 + Math.random() * 2.5;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);

    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);

    colors[i * 3] = baseCol.r * (0.8 + Math.random() * 0.4);
    colors[i * 3 + 1] = baseCol.g * (0.8 + Math.random() * 0.4);
    colors[i * 3 + 2] = baseCol.b * (0.8 + Math.random() * 0.4);
  }}

  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  const mat = new THREE.PointsMaterial({{
    size: 0.045,
    vertexColors: true,
    transparent: true,
    opacity: 0.75,
    blending: THREE.AdditiveBlending,
  }});

  particleSystem = new THREE.Points(geo, mat);
  scene.add(particleSystem);
}}

/**
 * 3. 4 Diagnostic Shading Modes (CTA, Perfusion, Fluoroscopy, FFR)
 */
function getMaterial(part) {{
  // MODE 1: CONTRAST-ENHANCED CT ANGIOGRAM (CTA)
  if (currentMode === 'cta' || currentMode === 'cinematic') {{
    if (part === 'lv' || part === 'rv') {{
      return new THREE.MeshPhysicalMaterial({{
        color: 0x184A78,
        emissive: new THREE.Color(CONFIG.risk_score > 0.66 ? 0x2A0D15 : 0x051B33),
        emissiveIntensity: 0.40,
        roughness: 0.14,
        metalness: 0.06,
        clearcoat: 1.0,
        clearcoatRoughness: 0.08,
        transmission: 0.72,
        ior: 1.38,
        thickness: 1.8,
        transparent: true,
        opacity: 0.90,
        depthWrite: false,
        bumpMap: createMyocardialBumpMap(),
        bumpScale: 0.002
      }});
    }}
    if (part === 'la' || part === 'ra') {{
      return new THREE.MeshPhysicalMaterial({{
        color: 0x1E3A5F,
        emissive: 0x06182B,
        emissiveIntensity: 0.35,
        roughness: 0.16,
        metalness: 0.05,
        clearcoat: 1.0,
        clearcoatRoughness: 0.10,
        transmission: 0.70,
        ior: 1.36,
        thickness: 1.5,
        transparent: true,
        opacity: 0.88,
        depthWrite: false
      }});
    }}
    if (part === 'aorta') {{
      return new THREE.MeshPhysicalMaterial({{
        color: 0xDC2626,
        emissive: 0x7F1D1D,
        emissiveIntensity: 0.65,
        roughness: 0.22,
        metalness: 0.15,
        clearcoat: 1.0,
        clearcoatRoughness: 0.10,
        transmission: 0.40,
        ior: 1.35,
        thickness: 1.2,
        transparent: true,
        opacity: 0.92
      }});
    }}
    if (part === 'pulmonary' || part === 'vena_cava' || part === 'pulmonary_vein') {{
      return new THREE.MeshPhysicalMaterial({{
        color: 0x1D4ED8,
        emissive: 0x1E3A8A,
        emissiveIntensity: 0.55,
        roughness: 0.22,
        metalness: 0.15,
        clearcoat: 1.0,
        clearcoatRoughness: 0.10,
        transmission: 0.45,
        ior: 1.35,
        thickness: 1.2,
        transparent: true,
        opacity: 0.90
      }});
    }}
    if (part === 'coronary') {{
      return new THREE.MeshStandardMaterial({{
        color: 0xFF1744,
        emissive: 0xFF1744,
        emissiveIntensity: 2.4,
        roughness: 0.10,
        metalness: 0.20
      }});
    }}
  }}

  // MODE 2: AHA 17-SEGMENT ISCHEMIC PERFUSION MAP
  if (currentMode === 'perfusion' || currentMode === 'bioelectric') {{
    if (part === 'lv') {{
      return new THREE.MeshStandardMaterial({{
        vertexColors: true,
        roughness: 0.40,
        metalness: 0.10
      }});
    }}
    if (part === 'rv') {{
      return new THREE.MeshStandardMaterial({{
        color: 0x059669,
        roughness: 0.45,
        metalness: 0.10
      }});
    }}
    if (part === 'coronary') {{
      return new THREE.MeshStandardMaterial({{
        color: 0xFF2255,
        emissive: 0xCC1133,
        emissiveIntensity: 0.6,
        roughness: 0.25
      }});
    }}
    return new THREE.MeshStandardMaterial({{
      color: 0x334155,
      roughness: 0.50,
      metalness: 0.20
    }});
  }}

  // MODE 3: FLUOROSCOPIC CATHETER ANGIOGRAPHY (FLUORO)
  if (currentMode === 'fluoro' || currentMode === 'angiogram') {{
    if (part === 'coronary') {{
      return new THREE.MeshStandardMaterial({{
        color: 0x38BDF8,
        emissive: 0x0284C7,
        emissiveIntensity: 1.80,
        roughness: 0.10,
        metalness: 0.30
      }});
    }}
    if (part === 'aorta' || part === 'pulmonary') {{
      return new THREE.MeshStandardMaterial({{
        color: 0x1E293B,
        emissive: 0x0F172A,
        emissiveIntensity: 0.45,
        transparent: true,
        opacity: 0.45,
        roughness: 0.50
      }});
    }}
    return new THREE.MeshStandardMaterial({{
      color: 0x070B14,
      transparent: true,
      opacity: 0.22,
      roughness: 0.90,
      metalness: 0.10,
      depthWrite: false
    }});
  }}

  // MODE 4: CORONARY FRACTIONAL FLOW RESERVE (FFR)
  if (currentMode === 'ffr' || currentMode === 'matrix') {{
    if (part === 'coronary') {{
      return new THREE.MeshStandardMaterial({{
        vertexColors: true,
        roughness: 0.15,
        metalness: 0.85
      }});
    }}
    return new THREE.MeshStandardMaterial({{
      color: 0x0F172A,
      transparent: true,
      opacity: 0.70,
      roughness: 0.50
    }});
  }}

  return new THREE.MeshStandardMaterial({{ color: 0xBE123C }});
}}

function setMode(mode) {{
  currentMode = mode;
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  if (window.event && window.event.target) window.event.target.classList.add('active');

  // Refresh all materials
  if (lvMesh) lvMesh.material = getMaterial('lv');
  if (rvMesh) rvMesh.material = getMaterial('rv');
  if (laMesh) laMesh.material = getMaterial('la');
  if (raMesh) raMesh.material = getMaterial('ra');
  if (laaMesh) laaMesh.material = getMaterial('la');
  if (raaMesh) raaMesh.material = getMaterial('ra');
  if (aortaMesh) aortaMesh.material = getMaterial('aorta');
  if (pulmonaryMesh) pulmonaryMesh.material = getMaterial('pulmonary');
  if (rpaMesh) rpaMesh.material = getMaterial('pulmonary');
  if (lpaMesh) lpaMesh.material = getMaterial('pulmonary');
  if (svcMesh) svcMesh.material = getMaterial('pulmonary');
  if (ivcMesh) ivcMesh.material = getMaterial('pulmonary');

  pulmonaryVeins.forEach(m => {{ m.material = getMaterial('pulmonary'); }});
  supraAorticBranches.forEach(m => {{ m.material = getMaterial('aorta'); }});
  coronaryVessels.forEach(m => {{ m.material = getMaterial('coronary'); }});

  // Apply AHA 17-Segment Perfusion colors if active
  if (currentMode === 'perfusion' || currentMode === 'bioelectric') {{
    if (lvMesh && lvMesh.geometry) {{
      applyAHAPerfusionColors(lvMesh.geometry);
    }}
  }}

  // Apply FFR continuous gradient if active
  if (currentMode === 'ffr' || currentMode === 'matrix') {{
    const distalFFR = Math.max(0.48, Math.min(0.98, 0.98 - ((CONFIG.ca * 0.09) + (CONFIG.oldpeak * 0.035))));
    coronaryVessels.forEach((m, idx) => {{
      const isStenosed = (idx === 1 && CONFIG.ca >= 1) || (idx === 5 && CONFIG.ca >= 2) || (idx === 3 && CONFIG.ca >= 3);
      if (m && m.geometry) {{
        applyFFRGradient(m.geometry, isStenosed, distalFFR);
      }}
    }});
  }}

  // Toggle conduction fibers in bioelectric mode
  conductionFibers.forEach(f => {{
    f.material.opacity = (currentMode === 'perfusion' || currentMode === 'bioelectric') ? 0.95 : 0.0;
  }});
}}

/**
 * 4. Dual-Phase Wiggers Systole/Diastole & Apical Wringing
 */
function updateCardiacBeating(delta) {{
  const beatsPerSecond = (CONFIG.bpm || 75) / 60.0;
  animationTime += delta * beatsPerSecond * Math.PI * 2;
  const phase = animationTime % (Math.PI * 2);

  let squeeze = 0;
  if (phase < 0.62) {{
    squeeze = Math.sin((phase / 0.62) * Math.PI);
  }} else if (phase > 4.4 && phase < 5.4) {{
    squeeze = 0.20 * Math.sin(((phase - 4.4) / 1.0) * Math.PI);
  }}

  // Ventricular apical wringing
  const lvScaleY = 1.0 - squeeze * 0.12;
  const lvScaleXZ = 1.0 - squeeze * 0.08;
  if (lvMesh) lvMesh.scale.set(lvScaleXZ, lvScaleY, lvScaleXZ);
  if (rvMesh) rvMesh.scale.set(lvScaleXZ, 1.0 - squeeze * 0.10, lvScaleXZ);

  if (laMesh) laMesh.scale.set(1.15 + squeeze * 0.05, 0.85 - squeeze * 0.06, 0.95 + squeeze * 0.05);
  if (raMesh) raMesh.scale.set(1.05 + squeeze * 0.05, 0.90 - squeeze * 0.06, 0.95 + squeeze * 0.05);

  if (heartGroup) {{
    heartGroup.rotation.y = Math.sin(animationTime * 0.15) * 0.18 + (squeeze * 0.07);
  }}

  stenosisMarkers.forEach(ring => {{
    const s = 1.0 + Math.sin(animationTime * 4.0) * 0.20;
    ring.scale.set(s, s, s);
  }});
  stenosisBeacons.forEach(b => {{
    b.intensity = 2.0 + Math.sin(animationTime * 4.0) * 1.5;
  }});

  // Trigger web audio heartbeat if enabled
  if (soundEnabled && audioCtx) {{
    const now = audioCtx.currentTime;
    if (now >= nextBeatTime) {{
      playHeartbeat(now);
      nextBeatTime = now + (60.0 / (CONFIG.bpm || 75));
    }}
  }}
}}

// ==============================================================================
// 5. CALIBRATED 25 mm/s LEAD II VECTOR CARDIOGRAM (ECG) WITH MEDICAL GRID
// ==============================================================================
function initECG() {{
  ecgCanvas = document.getElementById('ecg-canvas');
  if (!ecgCanvas) return;
  ecgCtx = ecgCanvas.getContext('2d');
  resizeECG();
  window.addEventListener('resize', resizeECG);
}}

function resizeECG() {{
  if (!ecgCanvas || !ecgCtx) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = ecgCanvas.getBoundingClientRect();
  const w = rect.width || ecgCanvas.clientWidth || 400;
  const h = rect.height || ecgCanvas.clientHeight || 70;
  ecgCanvas.width = Math.floor(w * dpr);
  ecgCanvas.height = Math.floor(h * dpr);
  ecgCtx.setTransform(1, 0, 0, 1, 0, 0);
  ecgCtx.scale(dpr, dpr);
  drawMedicalGrid();
}}

function drawMedicalGrid() {{
  if (!ecgCtx || !ecgCanvas) return;
  const rect = ecgCanvas.getBoundingClientRect();
  const w = rect.width || ecgCanvas.clientWidth || 400;
  const h = rect.height || ecgCanvas.clientHeight || 70;
  const mm = pxPerMm;

  ecgCtx.fillStyle = '#070C18';
  ecgCtx.fillRect(0, 0, w, h);

  // 1 mm Minor Grid Lines
  ecgCtx.lineWidth = 0.5;
  ecgCtx.strokeStyle = 'rgba(56, 189, 248, 0.05)';
  ecgCtx.beginPath();
  for (let x = 0; x < w; x += mm) {{ ecgCtx.moveTo(x, 0); ecgCtx.lineTo(x, h); }}
  for (let y = 0; y < h; y += mm) {{ ecgCtx.moveTo(0, y); ecgCtx.lineTo(w, y); }}
  ecgCtx.stroke();

  // 5 mm Major Grid Lines
  ecgCtx.lineWidth = 1.0;
  ecgCtx.strokeStyle = 'rgba(56, 189, 248, 0.12)';
  ecgCtx.beginPath();
  for (let x = 0; x < w; x += (mm * 5)) {{ ecgCtx.moveTo(x, 0); ecgCtx.lineTo(x, h); }}
  for (let y = 0; y < h; y += (mm * 5)) {{ ecgCtx.moveTo(0, y); ecgCtx.lineTo(w, y); }}
  ecgCtx.stroke();
}}

function drawECG(delta) {{
  if (!ecgCtx || !ecgCanvas) return;
  const rect = ecgCanvas.getBoundingClientRect();
  const w = rect.width || ecgCanvas.clientWidth || 400;
  const h = rect.height || ecgCanvas.clientHeight || 70;
  const midY = h * 0.55;

  const sweepDelta = Math.max(1.2, delta * speedMmPerSec * pxPerMm);
  const prevX = sweepX;
  sweepX = (sweepX + sweepDelta) % w;

  // Fade sweep head
  ecgCtx.fillStyle = 'rgba(7, 12, 24, 0.22)';
  ecgCtx.fillRect(sweepX, 0, 14, h);

  // Redraw grid under sweep clearing
  const mm = pxPerMm;
  ecgCtx.lineWidth = 0.5;
  ecgCtx.strokeStyle = 'rgba(56, 189, 248, 0.06)';
  ecgCtx.beginPath();
  const startGrid = Math.floor(sweepX / mm) * mm;
  for (let x = startGrid; x < sweepX + 14; x += mm) {{
    ecgCtx.moveTo(x, 0); ecgCtx.lineTo(x, h);
  }}
  ecgCtx.stroke();

  // Cardiac cycle length based on BPM
  const beatLengthPx = (60.0 / (CONFIG.bpm || 75)) * speedMmPerSec * pxPerMm;
  const phase = (sweepX % beatLengthPx) / beatLengthPx;

  let mV = 0.0;
  // P wave
  if (phase >= 0.10 && phase < 0.20) {{
    mV = 0.18 * Math.sin(((phase - 0.10) / 0.10) * Math.PI);
  }}
  // Q wave
  else if (phase >= 0.28 && phase < 0.31) {{
    mV = -0.14 * Math.sin(((phase - 0.28) / 0.03) * Math.PI);
  }}
  // R wave (smooth physiological spike)
  else if (phase >= 0.31 && phase < 0.36) {{
    mV = 1.25 * Math.pow(Math.sin(((phase - 0.31) / 0.05) * Math.PI), 1.3);
  }}
  // S wave
  else if (phase >= 0.36 && phase < 0.40) {{
    mV = -0.32 * Math.sin(((phase - 0.36) / 0.04) * Math.PI);
  }}
  // ST segment
  else if (phase >= 0.40 && phase < 0.60) {{
    const u = (phase - 0.40) / 0.20;
    const jPoint = -((CONFIG.oldpeak || 0) * 0.10);
    if (CONFIG.slope === 1) {{
      mV = jPoint + u * (0.12 + (CONFIG.oldpeak || 0) * 0.03); // Upsloping
    }} else if (CONFIG.slope === 2) {{
      mV = jPoint;                                             // Flat
    }} else {{
      mV = jPoint - u * (0.10 + (CONFIG.oldpeak || 0) * 0.03); // Downsloping
    }}
  }}
  // T wave
  else if (phase >= 0.60 && phase < 0.82) {{
    const inverted = (CONFIG.restecg === 1 || CONFIG.oldpeak >= 2.0 || CONFIG.risk_score >= 0.70);
    const amp = inverted ? -0.28 : 0.32;
    mV = amp * Math.sin(((phase - 0.60) / 0.22) * Math.PI);
  }}

  const currentY = midY - (mV * voltageScaleMmPerMv * pxPerMm);

  ecgCtx.beginPath();
  ecgCtx.moveTo(prevX, ecgLastY);
  ecgCtx.lineTo(sweepX, currentY);
  ecgCtx.lineWidth = 2.0;
  ecgCtx.strokeStyle = (CONFIG.oldpeak >= 1.5 || CONFIG.risk_score >= 0.70) ? '#EF4444' : '#38BDF8';
  ecgCtx.shadowColor = (CONFIG.oldpeak >= 1.5 || CONFIG.risk_score >= 0.70) ? '#DC2626' : '#0284C7';
  ecgCtx.shadowBlur = 6.0;
  ecgCtx.stroke();
  ecgCtx.shadowBlur = 0;

  ecgLastY = currentY;
}}

// ==============================================================================
// 6. WEB AUDIO API ACOUSTIC STETHOSCOPE SIMULATOR (S1/S2 LUB-DUB)
// ==============================================================================
function toggleCardiacAudio() {{
  if (!audioCtx) {{
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }}
  if (audioCtx.state === 'suspended') {{
    audioCtx.resume();
  }}

  soundEnabled = !soundEnabled;
  const btn = document.getElementById('sound-btn');
  const icon = document.getElementById('sound-icon');

  if (soundEnabled) {{
    btn.classList.add('active');
    icon.innerText = '[Live]';
    nextBeatTime = audioCtx.currentTime + 0.05;
  }} else {{
    btn.classList.remove('active');
    icon.innerText = '[Muted]';
  }}
}}

function playHeartbeat(time) {{
  // S1 ("Lub" - Mitral / Tricuspid closure)
  playTone(time, 62, 0.14, 0.82, 140);

  // S2 ("Dub" - Semilunar aortic / pulmonic closure via Bazett interval)
  const s2Offset = Math.min(0.24, 0.16 * Math.sqrt(75.0 / Math.max(30, CONFIG.bpm || 75)));
  playTone(time + s2Offset, 94, 0.09, 0.68, 170);

  // Pathological S3 Gallop in severe ischemia / ventricular dilation
  if (CONFIG.risk_score >= 0.75 || CONFIG.restecg === 2) {{
    playTone(time + s2Offset + 0.12, 38, 0.10, 0.35, 100);
  }}
}}

function playTone(time, freq, duration, gainVal, lowpassCutoff) {{
  try {{
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    const filter = audioCtx.createBiquadFilter();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, time);
    osc.frequency.exponentialRampToValueAtTime(Math.max(20, freq * 0.45), time + duration);

    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(lowpassCutoff, time);

    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.exponentialRampToValueAtTime(gainVal, time + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start(time);
    osc.stop(time + duration);
  }} catch (e) {{
    console.warn('Stethoscope audio synth error:', e);
  }}
}}

function onWindowResize() {{
  const container = document.getElementById('cgi-container');
  if (!container || !camera || !renderer) return;
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(container.clientWidth, container.clientHeight);
  resizeECG();
}}

function animate() {{
  if (isCgiContextLost) return;
  if (cgiAnimationId) cancelAnimationFrame(cgiAnimationId);
  cgiAnimationId = requestAnimationFrame(animate);

  const delta = clock.getDelta();
  if (controls) controls.update();

  updateCardiacBeating(delta);

  if (particleSystem) {{
    particleSystem.rotation.y += delta * 0.05;
  }}

  if (renderer && scene && camera) {{
    renderer.render(scene, camera);
  }}
  drawECG(delta);
}}
</script>
</body>
</html>"""
    return html
