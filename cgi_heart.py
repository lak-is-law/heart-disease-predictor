"""Ultra-high-fidelity 3D CGI Anatomical Heart and Dynamic Cardiac Telemetry Component
Renders an interactive Three.js WebGL anatomical heart with real-time systolic/diastolic
deformation, coronary stenosis visualization, procedural shaders, synchronized Lead-II
ECG oscilloscope, and Web Audio cardiac sound synthesis.
"""
from __future__ import annotations

import json


def render_cgi_heart(
    risk_score: float,
    risk_band: str,
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
) -> str:
    """Generate the complete self-contained HTML/WebGL bundle for Streamlit."""
    
    # Risk theme colors
    if risk_score < 0.33:
        primary_color = "#34d399"  # Emerald
        glow_color = "#10b981"
        risk_class = "low"
    elif risk_score < 0.66:
        primary_color = "#fbbf24"  # Amber
        glow_color = "#f59e0b"
        risk_class = "mid"
    else:
        primary_color = "#f43f5e"  # Crimson
        glow_color = "#e11d48"
        risk_class = "high"

    # Pre-encode configuration for JavaScript
    config = {
        "risk_score": float(risk_score),
        "risk_band": str(risk_band),
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

    html = f"""
<!DOCTYPE html>
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
    background: rgba(0, 111, 207, 0.4);
    border-color: #006FCF;
    box-shadow: 0 0 12px rgba(0, 111, 207, 0.4);
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
    background: rgba(5, 8, 17, 0.9);
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.06);
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
</style>
<!-- Three.js + OrbitControls -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
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
        {risk_band} ({int(risk_score * 100)}%)
      </div>
      <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 2px;">
        Model: <strong>{model_name}</strong>
      </div>
    </div>

    <!-- Mode Switcher -->
    <div class="mode-toolbar">
      <button class="mode-btn active" onclick="setMode('cinematic')">🩺 Anatomical CGI</button>
      <button class="mode-btn" onclick="setMode('bioelectric')">⚡ Bio-Electric</button>
      <button class="mode-btn" onclick="setMode('angiogram')">🩻 CT Angiogram</button>
      <button class="mode-btn" onclick="setMode('matrix')">🌐 Matrix Hologram</button>
      <button class="sound-btn" id="sound-btn" onclick="toggleCardiacAudio()">
        <span id="sound-icon">🔈</span> Sound
      </button>
    </div>
  </div>

  <!-- Orbit Hint -->
  <div class="orbit-hint">
    ✦ Click & Drag to Rotate 360° · Scroll to Zoom · Right Click to Pan
  </div>

  <!-- Bottom Telemetry HUD -->
  <div class="hud-bottom">
    <!-- Live Vector ECG -->
    <div class="ecg-card">
      <div class="ecg-header">
        <div class="ecg-title">
          <span style="color:{primary_color}; font-weight:800;">LEAD II</span>
          <span>· Real-time Vector Cardiogram</span>
        </div>
        <div class="ecg-meta">
          ST Dep: <strong style="color:{primary_color};">{oldpeak:.1f} mm</strong> | Slope: <strong>{['Upsloping', 'Flat', 'Downsloping'][slope - 1]}</strong>
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
// 3D CGI ANATOMICAL HEART ENGINE (THREE.JS + SHADERS)
// ==============================================================================
const CONFIG = {config_json};

let scene, camera, renderer, controls;
let heartGroup, ventricleMesh, atriumMesh, aortaMesh, pulmonaryMesh, venaCavaMesh;
let coronaryVessels = [], stenosisMarkers = [], conductionFibers = [];
let particleSystem;
let currentMode = 'cinematic';
let animationTime = 0;
let clock = new THREE.Clock();

// Audio Synth Context
let audioCtx = null;
let soundEnabled = false;
let nextBeatTime = 0;

init3D();
initECG();
animate();

function init3D() {{
  const container = document.getElementById('cgi-container');
  const canvas = document.getElementById('webgl-canvas');

  // Scene
  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x050811, 0.045);

  // Camera
  camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
  camera.position.set(0, 0.8, 5.2);

  // Renderer
  renderer = new THREE.WebGLRenderer({{
    canvas: canvas,
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance'
  }});
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;

  // OrbitControls
  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.minDistance = 2.5;
  controls.maxDistance = 8.5;
  controls.maxPolarAngle = Math.PI / 1.75;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.8;

  // Lighting
  setupLighting();

  // Build Anatomical Heart Mesh & Coronary Tree
  heartGroup = new THREE.Group();
  scene.add(heartGroup);

  buildAnatomy();
  buildCoronaryTree();
  buildConductionSystem();
  buildParticleField();

  // Window resize
  window.addEventListener('resize', onWindowResize);
}}

function setupLighting() {{
  const ambientLight = new THREE.AmbientLight(0x1e293b, 1.2);
  scene.add(ambientLight);

  const mainLight = new THREE.DirectionalLight(0xffffff, 2.0);
  mainLight.position.set(5, 8, 6);
  scene.add(mainLight);

  const rimLight = new THREE.DirectionalLight(new THREE.Color(CONFIG.primary_color), 2.5);
  rimLight.position.set(-6, -3, -5);
  scene.add(rimLight);

  const topGlow = new THREE.PointLight(new THREE.Color(CONFIG.glow_color), 1.8, 10);
  topGlow.position.set(0, 3, 2);
  scene.add(topGlow);
}}

/**
 * Procedural Anatomical 3D Heart Construction
 */
function buildAnatomy() {{
  // 1. Ventricular Body (Sculpted organic apex and base)
  const ventGeo = new THREE.SphereGeometry(1.2, 64, 64);
  const pos = ventGeo.attributes.position;
  
  // Deform sphere into anatomical heart shape (conical apex pointing left/down)
  for (let i = 0; i < pos.count; i++) {{
    let x = pos.getX(i);
    let y = pos.getY(i);
    let z = pos.getZ(i);

    // Conical apex elongation towards bottom-left
    if (y < 0) {{
      const taper = 1.0 + y * 0.45;
      x *= Math.max(0.2, taper);
      z *= Math.max(0.2, taper);
      x -= y * 0.22; // Apex tip tilts left
    }} else {{
      // Superior ventricular expansion
      x *= 1.08;
      z *= 0.95;
    }}

    // Anterior interventricular groove indentation
    if (z > 0 && Math.abs(x) < 0.4) {{
      z -= 0.08 * (1.0 - Math.abs(x) / 0.4);
    }}

    pos.setXYZ(i, x, y, z);
  }}
  ventGeo.computeVertexNormals();

  ventricleMesh = new THREE.Mesh(ventGeo, getMaterial('ventricle'));
  heartGroup.add(ventricleMesh);

  // 2. Atria (Superior Chambers)
  const atriaGeo = new THREE.SphereGeometry(0.72, 48, 48);
  atriumMesh = new THREE.Mesh(atriaGeo, getMaterial('atrium'));
  atriumMesh.scale.set(1.4, 0.75, 1.0);
  atriumMesh.position.set(-0.1, 0.95, -0.2);
  heartGroup.add(atriumMesh);

  // 3. Aortic Arch (Ascending, Curved Arch, Descending)
  const aortaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.1, 0.6, 0.1),
    new THREE.Vector3(0.25, 1.4, 0.1),
    new THREE.Vector3(0.05, 1.9, -0.1),
    new THREE.Vector3(-0.4, 1.8, -0.3),
    new THREE.Vector3(-0.55, 0.8, -0.45),
  ]);
  const aortaGeo = new THREE.TubeGeometry(aortaCurve, 40, 0.22, 24, false);
  aortaMesh = new THREE.Mesh(aortaGeo, getMaterial('vessel'));
  heartGroup.add(aortaMesh);

  // Three Branching Arteries off Aortic Arch
  [-0.15, 0.02, 0.18].forEach((xOff, idx) => {{
    const branchCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(xOff, 1.8, -0.1),
      new THREE.Vector3(xOff * 1.3, 2.3 + idx * 0.08, -0.05)
    ]);
    const branchGeo = new THREE.TubeGeometry(branchCurve, 16, 0.065, 16, false);
    const branchMesh = new THREE.Mesh(branchGeo, getMaterial('vessel'));
    heartGroup.add(branchMesh);
  }});

  // 4. Pulmonary Trunk & Bifurcation
  const pulmCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.15, 0.6, 0.35),
    new THREE.Vector3(-0.25, 1.3, 0.15),
    new THREE.Vector3(-0.4, 1.5, -0.05),
  ]);
  const pulmGeo = new THREE.TubeGeometry(pulmCurve, 30, 0.2, 20, false);
  pulmonaryMesh = new THREE.Mesh(pulmGeo, getMaterial('pulmonary'));
  heartGroup.add(pulmonaryMesh);

  // 5. Superior Vena Cava
  const svcCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.65, 0.7, -0.25),
    new THREE.Vector3(0.65, 1.7, -0.25),
  ]);
  const svcGeo = new THREE.TubeGeometry(svcCurve, 20, 0.18, 16, false);
  venaCavaMesh = new THREE.Mesh(svcGeo, getMaterial('pulmonary'));
  heartGroup.add(venaCavaMesh);
}}

/**
 * Coronary Artery Tree with Real-time Stenosis & Ischemia Highlighting
 */
function buildCoronaryTree() {{
  // Left Anterior Descending (LAD) traversing the anterior groove
  const ladCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.0, 0.8, 0.7),
    new THREE.Vector3(-0.1, 0.4, 0.95),
    new THREE.Vector3(-0.15, 0.0, 0.98),
    new THREE.Vector3(-0.22, -0.4, 0.88),
    new THREE.Vector3(-0.35, -0.85, 0.55),
    new THREE.Vector3(-0.42, -1.2, 0.18),
  ]);
  const ladGeo = new THREE.TubeGeometry(ladCurve, 40, 0.045, 16, false);
  const ladMesh = new THREE.Mesh(ladGeo, getMaterial('coronary'));
  heartGroup.add(ladMesh);
  coronaryVessels.push(ladMesh);

  // Right Coronary Artery (RCA)
  const rcaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.35, 0.7, 0.5),
    new THREE.Vector3(0.7, 0.45, 0.6),
    new THREE.Vector3(0.85, 0.0, 0.45),
    new THREE.Vector3(0.75, -0.45, 0.35),
    new THREE.Vector3(0.4, -0.8, 0.2),
  ]);
  const rcaGeo = new THREE.TubeGeometry(rcaCurve, 40, 0.04, 16, false);
  const rcaMesh = new THREE.Mesh(rcaGeo, getMaterial('coronary'));
  heartGroup.add(rcaMesh);
  coronaryVessels.push(rcaMesh);

  // Circumflex Artery (LCx)
  const lcxCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.2, 0.7, 0.6),
    new THREE.Vector3(-0.65, 0.55, 0.4),
    new THREE.Vector3(-0.85, 0.2, 0.0),
    new THREE.Vector3(-0.7, -0.3, -0.3),
  ]);
  const lcxGeo = new THREE.TubeGeometry(lcxCurve, 30, 0.035, 16, false);
  const lcxMesh = new THREE.Mesh(lcxGeo, getMaterial('coronary'));
  heartGroup.add(lcxMesh);
  coronaryVessels.push(lcxMesh);

  // Highlight Stenosis Occlusion Rings if ca > 0 (Number of major vessels fluoroscopically coloured)
  if (CONFIG.ca > 0) {{
    const stenosisPositions = [
      new THREE.Vector3(-0.15, 0.0, 1.0),    // LAD mid-vessel stenosis
      new THREE.Vector3(0.85, 0.0, 0.47),     // RCA proximal stenosis
      new THREE.Vector3(-0.65, 0.55, 0.42),   // LCx bifurcation stenosis
    ];

    for (let i = 0; i < Math.min(CONFIG.ca, 3); i++) {{
      const ringGeo = new THREE.TorusGeometry(0.08, 0.025, 16, 32);
      const ringMat = new THREE.MeshBasicMaterial({{
        color: 0xff0033,
        wireframe: false,
      }});
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.copy(stenosisPositions[i]);
      ring.lookAt(heartGroup.position);
      heartGroup.add(ring);
      stenosisMarkers.push(ring);

      // Warning glow beacon
      const beaconLight = new THREE.PointLight(0xff0044, 2.5, 1.2);
      beaconLight.position.copy(stenosisPositions[i]);
      heartGroup.add(beaconLight);
    }}
  }}
}}

/**
 * Bio-Electrical Conduction Pathways (SA Node -> AV Node -> His-Purkinje)
 */
function buildConductionSystem() {{
  const fiberPaths = [
    [new THREE.Vector3(0.5, 1.1, -0.1), new THREE.Vector3(0.1, 0.8, 0.2)], // SA to AV node
    [new THREE.Vector3(0.1, 0.8, 0.2), new THREE.Vector3(0.0, 0.3, 0.4)],  // Bundle of His
    [new THREE.Vector3(0.0, 0.3, 0.4), new THREE.Vector3(-0.35, -0.9, 0.3)], // Left Bundle Branch
    [new THREE.Vector3(0.0, 0.3, 0.4), new THREE.Vector3(0.45, -0.7, 0.2)],  // Right Bundle Branch
  ];

  fiberPaths.forEach(pts => {{
    const curve = new THREE.CatmullRomCurve3(pts);
    const geo = new THREE.TubeGeometry(curve, 20, 0.02, 8, false);
    const mat = new THREE.MeshBasicMaterial({{
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.0, // Visible in bioelectric mode
      wireframe: true
    }});
    const mesh = new THREE.Mesh(geo, mat);
    heartGroup.add(mesh);
    conductionFibers.push(mesh);
  }});
}}

/**
 * Floating Volumetric Bio-Luminescent Particles
 */
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
 * Dynamic Shaders and Materials by Mode
 */
function getMaterial(part) {{
  if (currentMode === 'cinematic') {{
    if (part === 'ventricle') {{
      const baseColor = CONFIG.risk_score > 0.6 ? 0xb91c1c : (CONFIG.risk_score > 0.33 ? 0xc2410c : 0xbe123c);
      return new THREE.MeshPhysicalMaterial({{
        color: baseColor,
        emissive: new THREE.Color(CONFIG.glow_color),
        emissiveIntensity: 0.12,
        roughness: 0.35,
        metalness: 0.1,
        clearcoat: 0.8,
        clearcoatRoughness: 0.15,
        transmission: 0.08,
      }});
    }}
    if (part === 'atrium') {{
      return new THREE.MeshPhysicalMaterial({{
        color: 0x9f1239,
        roughness: 0.4,
        clearcoat: 0.6,
      }});
    }}
    if (part === 'vessel') {{
      return new THREE.MeshPhysicalMaterial({{
        color: 0xdc2626,
        roughness: 0.25,
        metalness: 0.15,
        clearcoat: 0.9,
      }});
    }}
    if (part === 'pulmonary') {{
      return new THREE.MeshPhysicalMaterial({{
        color: 0x1d4ed8,
        roughness: 0.3,
        metalness: 0.1,
        clearcoat: 0.7,
      }});
    }}
    if (part === 'coronary') {{
      return new THREE.MeshStandardMaterial({{
        color: 0xff0044,
        roughness: 0.2,
        emissive: 0xff0022,
        emissiveIntensity: 0.35,
      }});
    }}
  }} else if (currentMode === 'bioelectric') {{
    return new THREE.MeshBasicMaterial({{
      color: 0x0284c7,
      wireframe: true,
      transparent: true,
      opacity: part === 'ventricle' ? 0.35 : 0.25
    }});
  }} else if (currentMode === 'angiogram') {{
    // Radiographic CT scan view: dark myocardium, bright glowing contrast vessels
    if (part === 'coronary' || part === 'vessel') {{
      return new THREE.MeshBasicMaterial({{
        color: 0x38bdf8,
        wireframe: false,
      }});
    }}
    return new THREE.MeshBasicMaterial({{
      color: 0x1e293b,
      transparent: true,
      opacity: 0.2,
      wireframe: true,
    }});
  }} else if (currentMode === 'matrix') {{
    return new THREE.MeshBasicMaterial({{
      color: new THREE.Color(CONFIG.primary_color),
      wireframe: true,
      transparent: true,
      opacity: 0.55
    }});
  }}
  return new THREE.MeshStandardMaterial({{ color: 0xbe123c }});
}}

function setMode(mode) {{
  currentMode = mode;
  document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');

  // Update materials across all components
  ventricleMesh.material = getMaterial('ventricle');
  atriumMesh.material = getMaterial('atrium');
  aortaMesh.material = getMaterial('vessel');
  pulmonaryMesh.material = getMaterial('pulmonary');
  venaCavaMesh.material = getMaterial('pulmonary');

  coronaryVessels.forEach(m => m.material = getMaterial('coronary'));

  // Toggle conduction fibers in bioelectric mode
  conductionFibers.forEach(f => {{
    f.material.opacity = mode === 'bioelectric' ? 0.95 : 0.0;
  }});
}}

// ==============================================================================
// REAL-TIME DUAL-PHASE SYSTOLE / DIASTOLE DEFORMATION
// ==============================================================================
function updateCardiacBeating(delta) {{
  const beatsPerSecond = CONFIG.bpm / 60.0;
  animationTime += delta * beatsPerSecond * Math.PI * 2;

  // Realistic Wiggers cardiac cycle curve
  const phase = animationTime % (Math.PI * 2);
  
  // Dual contraction: Atrial systole (minor) then Ventricular systole (major)
  let squeeze = 0;
  if (phase < 0.6) {{
    // Ventricular systole (strong contraction)
    squeeze = Math.sin(phase / 0.6 * Math.PI);
  }} else if (phase > 4.5 && phase < 5.4) {{
    // Atrial systole (pre-ejection filling)
    squeeze = 0.22 * Math.sin((phase - 4.5) / 0.9 * Math.PI);
  }}

  // Ventricular apical torsion & volumetric compression
  const scaleY = 1.0 - squeeze * 0.14;
  const scaleXZ = 1.0 - squeeze * 0.08;
  ventricleMesh.scale.set(scaleXZ, scaleY, scaleXZ);
  atriumMesh.scale.set(1.4 + squeeze * 0.05, 0.75 - squeeze * 0.06, 1.0);

  // Twist along Y axis during systole
  heartGroup.rotation.y = Math.sin(animationTime * 0.15) * 0.2 + (squeeze * 0.06);

  // Stenosis markers pulsing alarm
  stenosisMarkers.forEach(ring => {{
    const s = 1.0 + Math.sin(animationTime * 4.0) * 0.25;
    ring.scale.set(s, s, s);
  }});

  // Trigger web audio heartbeat if enabled
  if (soundEnabled && audioCtx) {{
    const now = audioCtx.currentTime;
    if (now >= nextBeatTime) {{
      playHeartbeat(now);
      nextBeatTime = now + (60.0 / CONFIG.bpm);
    }}
  }}
}}

// ==============================================================================
// LEAD-II VECTOR ELECTROCARDIOGRAM (ECG) SIMULATOR
// ==============================================================================
let ecgCanvas, ecgCtx;
let ecgPoints = [];
let sweepX = 0;

function initECG() {{
  ecgCanvas = document.getElementById('ecg-canvas');
  ecgCtx = ecgCanvas.getContext('2d');
  resizeECG();
  window.addEventListener('resize', resizeECG);
}}

function resizeECG() {{
  ecgCanvas.width = ecgCanvas.clientWidth * window.devicePixelRatio;
  ecgCanvas.height = ecgCanvas.clientHeight * window.devicePixelRatio;
}}

function drawECG(delta) {{
  if (!ecgCtx) return;

  const w = ecgCanvas.width;
  const h = ecgCanvas.height;
  const midY = h * 0.52;

  // Fade sweep tail
  ecgCtx.fillStyle = 'rgba(5, 8, 17, 0.08)';
  ecgCtx.fillRect(0, 0, w, h);

  // Speed of ECG sweep corresponds to BPM (25mm/sec standard)
  const sweepSpeed = (CONFIG.bpm / 75.0) * 3.5 * window.devicePixelRatio;
  const prevX = sweepX;
  sweepX = (sweepX + sweepSpeed) % w;

  // Clear upcoming column
  ecgCtx.clearRect(sweepX, 0, 14 * window.devicePixelRatio, h);

  // Calculate ECG Voltage at current phase
  const cycleWidth = w / (CONFIG.bpm / 30);
  const cyclePos = (sweepX % cycleWidth) / cycleWidth; // 0 to 1

  let voltage = 0;

  // P-wave (Atrial depolarization)
  if (cyclePos >= 0.10 && cyclePos < 0.20) {{
    voltage = 0.15 * Math.sin((cyclePos - 0.10) / 0.10 * Math.PI);
  }}
  // PR-segment (Isoelectric baseline)
  else if (cyclePos >= 0.20 && cyclePos < 0.28) {{
    voltage = 0.0;
  }}
  // Q-wave (Septal depolarization)
  else if (cyclePos >= 0.28 && cyclePos < 0.31) {{
    voltage = -0.15 * Math.sin((cyclePos - 0.28) / 0.03 * Math.PI);
  }}
  // R-wave (Rapid ventricular depolarization)
  else if (cyclePos >= 0.31 && cyclePos < 0.36) {{
    voltage = 1.0 * Math.sin((cyclePos - 0.31) / 0.05 * Math.PI);
  }}
  // S-wave
  else if (cyclePos >= 0.36 && cyclePos < 0.40) {{
    voltage = -0.35 * Math.sin((cyclePos - 0.36) / 0.04 * Math.PI);
  }}
  // ST-Segment (Clinically depressed by oldpeak and modulated by slope)
  else if (cyclePos >= 0.40 && cyclePos < 0.60) {{
    const stProgress = (cyclePos - 0.40) / 0.20;
    const baseDepression = - (CONFIG.oldpeak * 0.08); // ST depression in mm

    if (CONFIG.slope === 1) {{
      // Upsloping
      voltage = baseDepression + stProgress * 0.15;
    }} else if (CONFIG.slope === 2) {{
      // Flat (Horizontal ST depression)
      voltage = baseDepression;
    }} else {{
      // Downsloping (Severe ischemia marker)
      voltage = baseDepression - stProgress * 0.12;
    }}
  }}
  // T-wave (Ventricular repolarization)
  else if (cyclePos >= 0.60 && cyclePos < 0.80) {{
    const tWaveAmp = CONFIG.restecg === 1 ? -0.25 : 0.30; // Inverted T if ST-T abnormality
    voltage = tWaveAmp * Math.sin((cyclePos - 0.60) / 0.20 * Math.PI);
  }}

  const targetY = midY - (voltage * h * 0.38);

  ecgCtx.beginPath();
  ecgCtx.strokeStyle = CONFIG.primary_color;
  ecgCtx.lineWidth = 2.2 * window.devicePixelRatio;
  ecgCtx.lineCap = 'round';
  ecgCtx.shadowColor = CONFIG.glow_color;
  ecgCtx.shadowBlur = 8 * window.devicePixelRatio;

  ecgCtx.moveTo(prevX, ecgPoints[Math.floor(prevX)] || targetY);
  ecgCtx.lineTo(sweepX, targetY);
  ecgCtx.stroke();
  ecgCtx.shadowBlur = 0;

  ecgPoints[Math.floor(sweepX)] = targetY;
}}

// ==============================================================================
// WEB AUDIO API REAL-TIME CARDIAC SOUND SYNTHESIZER (LUB-DUB)
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
    icon.innerText = '🔊';
    nextBeatTime = audioCtx.currentTime + 0.1;
  }} else {{
    btn.classList.remove('active');
    icon.innerText = '🔈';
  }}
}}

function playHeartbeat(time) {{
  // S1 (Mitral / Tricuspid closure - "Lub")
  playTone(time, 65, 0.14, 0.8);
  // S2 (Aortic / Pulmonic closure - "Dub") ~150ms after S1
  playTone(time + 0.16, 92, 0.10, 0.65);
}}

function playTone(time, freq, duration, gainVal) {{
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  const filter = audioCtx.createBiquadFilter();

  osc.type = 'sine';
  osc.frequency.setValueAtTime(freq, time);
  osc.frequency.exponentialRampToValueAtTime(35, time + duration);

  filter.type = 'lowpass';
  filter.frequency.setValueAtTime(140, time);

  gain.gain.setValueAtTime(0.001, time);
  gain.gain.exponentialRampToValueAtTime(gainVal, time + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.001, time + duration);

  osc.connect(filter);
  filter.connect(gain);
  gain.connect(audioCtx.destination);

  osc.start(time);
  osc.stop(time + duration);
}}

function onWindowResize() {{
  const container = document.getElementById('cgi-container');
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(container.clientWidth, container.clientHeight);
}}

function animate() {{
  requestAnimationFrame(animate);

  const delta = clock.getDelta();
  controls.update();

  updateCardiacBeating(delta);

  if (particleSystem) {{
    particleSystem.rotation.y += delta * 0.05;
  }}

  renderer.render(scene, camera);
  drawECG(delta);
}}
</script>
</body>
</html>
    """
    return html
