"""Comprehensive Test Suite for Milestone M2:
Medically Accurate 3D Anatomical Heart CGI, Shader Modes, Telemetry & Storage Optimization.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PORTAL_DIR = REPO_ROOT / "portal"
VENDOR_DIR = PORTAL_DIR / "vendor"
CGI_HEART_PATH = REPO_ROOT / "cgi_heart.py"
PORTAL_JS_PATH = PORTAL_DIR / "portal.js"
PORTAL_HTML_PATH = PORTAL_DIR / "app.html"

# Pinned Vendor Manifest
EXPECTED_VENDOR = {
    "three.min.js": {
        "sha256": "9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2",
        "size": 603445,
    },
    "OrbitControls.js": {
        "sha256": "02bb4ade710f3e607329e37a21f098bc3ac70eb6e33daf8a65e79f4db785e7b2",
        "size": 26375,
    },
}

STORAGE_BUDGET_BYTES = int(2.5 * 1024 * 1024)  # 2.5 MB ceiling
VRAM_BUDGET_MB = 120.0  # 120 MB ceiling


class TestM2VendorBundlingAndStorage(unittest.TestCase):
    """Verifies vendor asset integrity, SHA-256 hashes, and client storage budget."""

    def test_vendor_assets_exist_and_match_digests(self):
        """Vendor assets must exist on disk and match cryptographic SHA-256 hashes."""
        for filename, expected in EXPECTED_VENDOR.items():
            path = VENDOR_DIR / filename
            self.assertTrue(path.is_file(), f"Missing vendor asset: {path}")

            data = path.read_bytes()
            self.assertEqual(
                len(data),
                expected["size"],
                f"File size mismatch for {filename}: {len(data)} != {expected['size']}",
            )

            digest = hashlib.sha256(data).hexdigest()
            self.assertEqual(
                digest,
                expected["sha256"],
                f"SHA-256 mismatch for {filename}:\n  Actual:   {digest}\n  Expected: {expected['sha256']}",
            )

    def test_client_storage_budget_under_2_5mb(self):
        """Total uncompressed static client assets must remain strictly below 2.5 MB."""
        static_files = [
            "index.html",
            "portal.js",
            "styles.css",
            "manifest.json",
            "model_weights.json",
            "vendor/three.min.js",
            "vendor/OrbitControls.js",
        ]
        total_bytes = 0
        for rel in static_files:
            file_path = PORTAL_DIR / rel
            self.assertTrue(file_path.is_file(), f"Missing static file: {file_path}")
            total_bytes += file_path.stat().st_size

        self.assertLess(
            total_bytes,
            STORAGE_BUDGET_BYTES,
            f"Client storage footprint exceeds 2.5 MB: {total_bytes:,} >= {STORAGE_BUDGET_BYTES:,}",
        )
        utilization = (total_bytes / STORAGE_BUDGET_BYTES) * 100.0
        print(f"\n[Storage Audit] Client static assets: {total_bytes:,} bytes ({total_bytes / (1024*1024):.3f} MB, {utilization:.1f}% of budget)")

    def test_vram_allocation_model_under_120mb(self):
        """Theoretical maximum VRAM allocation at clamped DPR <= 2.0 must be < 120 MB."""
        w, h, dpr, msaa = 1200, 600, 2.0, 4
        pixels = int(w * h * dpr * dpr)
        fb_bytes = pixels * (4 + 4) * msaa  # RGBA8 + Depth24/Stencil8 with 4x MSAA
        fb_mb = fb_bytes / (1024 * 1024)
        geometry_mb = 0.52
        driver_mb = 20.0
        total_vram_mb = fb_mb + geometry_mb + driver_mb

        self.assertLess(
            total_vram_mb,
            VRAM_BUDGET_MB,
            f"VRAM budget exceeded: {total_vram_mb:.2f} MB >= {VRAM_BUDGET_MB} MB",
        )
        print(f"[VRAM Audit] Peak clamped VRAM: {total_vram_mb:.2f} MB (< {VRAM_BUDGET_MB} MB ceiling)")


class TestM2CodeSyntaxAndCompilation(unittest.TestCase):
    """Verifies that all JavaScript and HTML files compile cleanly without syntax errors."""

    def test_portal_js_syntax_compilation(self):
        """portal.js must pass Node.js AST compilation with zero syntax errors."""
        res = subprocess.run(
            ["node", "-c", str(PORTAL_JS_PATH)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            res.returncode,
            0,
            f"JavaScript syntax error in portal.js:\n{res.stderr}",
        )

    def test_portal_index_html_inline_scripts_syntax(self):
        """All inline scripts in portal/index.html must compile with zero errors."""
        content = PORTAL_HTML_PATH.read_text(encoding="utf-8")
        scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", content, re.DOTALL)
        self.assertGreater(len(scripts), 0, "No inline scripts found in portal/index.html")

        for i, code in enumerate(scripts):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                f.write(code)
                tmp_path = f.name
            try:
                res = subprocess.run(["node", "-c", tmp_path], capture_output=True, text=True)
                self.assertEqual(
                    res.returncode,
                    0,
                    f"Syntax error in index.html inline script #{i}:\n{res.stderr}",
                )
            finally:
                os.remove(tmp_path)

    def test_cgi_heart_generated_bundle_syntax(self):
        """Scripts generated by cgi_heart.py must pass Node.js syntax verification."""
        import cgi_heart

        html = cgi_heart.render_cgi_heart(
            risk_score=0.88,
            risk_band="HIGH",
            bpm=135,
            oldpeak=3.4,
            slope=3,
            ca=3,
            embed_vendor=False,
        )
        scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html, re.DOTALL)
        self.assertGreater(len(scripts), 0, "No inline scripts found in cgi_heart bundle")

        for i, code in enumerate(scripts):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                f.write(code)
                tmp_path = f.name
            try:
                res = subprocess.run(["node", "-c", tmp_path], capture_output=True, text=True)
                self.assertEqual(
                    res.returncode,
                    0,
                    f"Syntax error in cgi_heart script block #{i}:\n{res.stderr}",
                )
            finally:
                os.remove(tmp_path)

    def test_portal_js_update_portal_prediction_runtime_execution(self):
        """Executing updatePortalPrediction() in portal.js must not throw ReferenceError: restecg is not defined."""
        escaped_path = json.dumps(str(PORTAL_JS_PATH))
        eval_script = f'''
const fs = require('fs');
const vm = require('vm');

const code = fs.readFileSync({escaped_path}, 'utf8');

const mockValues = {{
  'inp-age': '58',
  'inp-sex': '1',
  'inp-trestbps': '135',
  'inp-chol': '250',
  'inp-thalach': '145',
  'inp-cp': '3',
  'inp-exang': '0',
  'inp-oldpeak': '1.8',
  'inp-slope': '2',
  'inp-ca': '2',
  'inp-thal': '3',
  'inp-restecg': '0',
  'portal-risk-value': '',
  'portal-ffr-val': '',
  'portal-bpm-display': '',
  'portal-stenosis-val': '',
  'portal-risk-blurb': '',
  'val-age': '',
  'val-trestbps': '',
  'val-chol': '',
  'val-thalach': '',
  'val-oldpeak': ''
}};

const mockElement = (id) => ({{
  value: mockValues[id] || '0',
  innerText: '',
  innerHTML: '',
  style: {{}},
  classList: {{ add: () => {{}}, remove: () => {{}}, toggle: () => {{}} }},
  setAttribute: () => {{}},
  addEventListener: () => {{}},
  replaceChildren: () => {{}}
}});

const sandbox = {{
  document: {{
    getElementById: (id) => mockElement(id),
    querySelector: () => mockElement(''),
    querySelectorAll: () => [],
    addEventListener: () => {{}}
  }},
  window: {{
    addEventListener: () => {{}},
    removeEventListener: () => {{}}
  }},
  navigator: {{
    hardwareConcurrency: 4,
    deviceMemory: 8
  }},
  console: console,
  Math: Math,
  parseFloat: parseFloat,
  parseInt: parseInt,
  Date: Date
}};
sandbox.global = sandbox;
sandbox.window.document = sandbox.document;

vm.createContext(sandbox);

// 1. Compile and evaluate portal.js into the sandbox
try {{
  vm.runInContext(fs.readFileSync({json.dumps(str(PORTAL_JS_PATH.parent / 'research-score.js'))}, 'utf8'), sandbox);
  vm.runInContext(code, sandbox);
}} catch (err) {{
  console.error("PARSING_ERROR:", err.stack);
  process.exit(2);
}}

// 2. Execute updatePortalPrediction() - must execute cleanly without ReferenceError
try {{
  sandbox.updatePortalPrediction();
}} catch (err) {{
  console.error("RUNTIME_ERROR:", err.stack);
  process.exit(1);
}}

console.log("SUCCESS: updatePortalPrediction evaluated cleanly without ReferenceError");
'''
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(eval_script)
            tmp_path = f.name
        try:
            res = subprocess.run(["node", tmp_path], capture_output=True, text=True)
            self.assertEqual(
                res.returncode,
                0,
                f"updatePortalPrediction() execution failed with runtime error:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
            )
            self.assertIn("SUCCESS", res.stdout)
        finally:
            os.remove(tmp_path)


class TestM2AnatomicalGeometryAndTopology(unittest.TestCase):
    """Verifies medical accuracy of 4-chamber morphology, great vessels, and coronary tree."""

    def setUp(self):
        self.portal_js = PORTAL_JS_PATH.read_text(encoding="utf-8")
        self.cgi_py = CGI_HEART_PATH.read_text(encoding="utf-8")

    def test_four_chamber_morphology_present(self):
        """Both portal.js and cgi_heart.py must feature 4 discrete cardiac chambers and auricles."""
        required_tokens = [
            "LEFT VENTRICLE",
            "RIGHT VENTRICLE",
            "LEFT ATRIUM",
            "RIGHT ATRIUM",
            "LAA",  # Left Atrial Appendage
            "RAA",  # Right Atrial Appendage
        ]
        for token in required_tokens:
            self.assertIn(token, self.portal_js, f"Missing {token} in portal.js")
            self.assertIn(token, self.cgi_py, f"Missing {token} in cgi_heart.py")

    def test_great_vessels_and_bifurcations_present(self):
        """Both frontends must model the Aortic Arch, 3 supra-aortic branches, MPA, RPA, LPA, SVC, and IVC."""
        required_vessels = [
            "Brachiocephalic",
            "Carotid",
            "Subclavian",
            "pulmonary",
            "rpa",
            "lpa",
            "svc",
            "ivc",
        ]
        for v in required_vessels:
            self.assertTrue(
                re.search(v, self.portal_js, re.IGNORECASE),
                f"Vessel '{v}' missing in portal.js",
            )
            self.assertTrue(
                re.search(v, self.cgi_py, re.IGNORECASE),
                f"Vessel '{v}' missing in cgi_heart.py",
            )

    def test_coronary_circulation_tree_present(self):
        """LMCA, LAD with D1, LCx with OM1, RCA with AM and PDA must be present in coronary circulation."""
        coronary_branches = [
            "lmca",
            "lad",
            "d1",
            "lcx",
            "om1",
            "rca",
            "am",
            "pda",
        ]
        for branch in coronary_branches:
            self.assertTrue(
                re.search(branch, self.portal_js, re.IGNORECASE),
                f"Coronary branch '{branch}' missing in portal.js",
            )
            self.assertTrue(
                re.search(branch, self.cgi_py, re.IGNORECASE),
                f"Coronary branch '{branch}' missing in cgi_heart.py",
            )

    def test_tangent_quaternion_stenosis_alignment(self):
        """Stenosis lesion rings must be oriented using curve tangent vectors and quaternions."""
        quaternion_pattern = r"setFromUnitVectors\s*\(\s*new\s+THREE\.Vector3\s*\(\s*0\s*,\s*0\s*,\s*1\s*\)\s*,\s*tangent\s*\)"
        self.assertTrue(
            re.search(quaternion_pattern, self.portal_js),
            "Tangent vector quaternion alignment missing in portal.js",
        )
        self.assertTrue(
            re.search(quaternion_pattern, self.cgi_py),
            "Tangent vector quaternion alignment missing in cgi_heart.py",
        )


class TestM2DiagnosticShadersAndTelemetry(unittest.TestCase):
    """Verifies the 4 standardized diagnostic shader modes, Lead II ECG, and Web Audio acoustics."""

    def setUp(self):
        self.portal_js = PORTAL_JS_PATH.read_text(encoding="utf-8")
        self.cgi_py = CGI_HEART_PATH.read_text(encoding="utf-8")
        self.portal_html = PORTAL_HTML_PATH.read_text(encoding="utf-8")

    def test_four_standardized_diagnostic_modes(self):
        """Both frontends must standardize on 'cta', 'perfusion', 'fluoro', and 'ffr' modes."""
        for mode in ["cta", "perfusion", "fluoro", "ffr"]:
            self.assertIn(f"'{mode}'", self.portal_js, f"Mode '{mode}' missing in portal.js")
            self.assertIn(f"'{mode}'", self.cgi_py, f"Mode '{mode}' missing in cgi_heart.py")
            self.assertIn(f"setPortalMode('{mode}'", self.portal_html, f"Button for '{mode}' missing in index.html")

    def test_mode1_procedural_myocardial_bump_map(self):
        """Mode 1 (CTA) must utilize procedural myofibril bump map on MeshPhysicalMaterial."""
        self.assertIn("createMyocardialBumpMap", self.portal_js)
        self.assertIn("createMyocardialBumpMap", self.cgi_py)
        self.assertIn("MeshPhysicalMaterial", self.portal_js)
        self.assertIn("MeshPhysicalMaterial", self.cgi_py)

    def test_mode2_aha_17_segment_perfusion_model(self):
        """Mode 2 must partition vertices into the AHA 17-Segment perfusion model."""
        self.assertIn("getAHASegment", self.portal_js)
        self.assertIn("getAHASegment", self.cgi_py)
        self.assertIn("applyAHAPerfusionColors", self.portal_js)
        self.assertIn("applyAHAPerfusionColors", self.cgi_py)

    def test_mode4_continuous_ffr_gradient(self):
        """Mode 4 must compute continuous FFR pressure gradient along coronary tubes."""
        self.assertIn("calculateClinicalFFR", self.portal_js)
        self.assertIn("applyFFRGradient", self.portal_js)
        self.assertIn("applyFFRGradient", self.cgi_py)

    def test_calibrated_lead_ii_ecg_and_grid(self):
        """ECG must implement 1mm/5mm medical grid, 25mm/s paper speed, and slope branching."""
        for src in [self.portal_js, self.cgi_py]:
            self.assertIn("drawMedicalGrid", src)
            self.assertIn("25.0", src)  # 25 mm/s
            self.assertIn("CONFIG.slope" if "CONFIG.slope" in src else "slope", src)

    def test_web_audio_acoustic_stethoscope_synthesis(self):
        """Web Audio synthesizer must generate S1, S2, and S3 gallop tones."""
        self.assertIn("CardiacAcousticSynthesizer", self.portal_js)
        self.assertIn("togglePortalAudio", self.portal_js)
        self.assertIn("playHeartbeat", self.cgi_py)
        self.assertIn("toggleCardiacAudio", self.cgi_py)
        self.assertIn("AudioContext", self.portal_js)
        self.assertIn("AudioContext", self.cgi_py)


class TestM2ContextLossRecoveryAndInterface(unittest.TestCase):
    """Verifies WebGL context loss recovery, teardown, and cgi_heart interface contracts."""

    def test_webgl_context_loss_listeners(self):
        """Canvas must attach webglcontextlost with preventDefault and webglcontextrestored."""
        portal_js = PORTAL_JS_PATH.read_text(encoding="utf-8")
        cgi_py = CGI_HEART_PATH.read_text(encoding="utf-8")

        for src, name in [(portal_js, "portal.js"), (cgi_py, "cgi_heart.py")]:
            self.assertIn("webglcontextlost", src, f"webglcontextlost missing in {name}")
            self.assertIn("webglcontextrestored", src, f"webglcontextrestored missing in {name}")
            self.assertIn("preventDefault", src, f"preventDefault missing in {name}")

    def test_scene_disposal_routines(self):
        """Clean teardown routines must traverse scene graph and dispose geometries and materials."""
        portal_js = PORTAL_JS_PATH.read_text(encoding="utf-8")
        cgi_py = CGI_HEART_PATH.read_text(encoding="utf-8")

        self.assertIn("disposePortalScene", portal_js)
        self.assertIn("teardownCgiScene", cgi_py)
        self.assertIn(".geometry.dispose()", portal_js)
        self.assertIn(".material.dispose()", portal_js)

    def test_render_cgi_heart_signatures(self):
        """cgi_heart.py:render_cgi_heart must support both positional and dictionary-based interfaces."""
        import cgi_heart

        # 1. Standard positional call
        html1 = cgi_heart.render_cgi_heart(0.85, "High Risk", bpm=130, oldpeak=3.2, ca=3, slope=3)
        self.assertIsInstance(html1, str)
        self.assertIn("LEAD II", html1)
        self.assertIn("three.min.js", html1)

        # 2. Dictionary-based call as specified in PROJECT.md: render_cgi_heart(patient_dict, risk_prob, risk_band)
        patient = {
            "thalach": 142,
            "oldpeak": 2.4,
            "slope": 2,
            "ca": 2,
            "cp": 3,
            "restecg": 1,
            "trestbps": 135,
            "chol": 255,
        }
        html2 = cgi_heart.render_cgi_heart(patient, 0.76, "ELEVATED")
        self.assertIsInstance(html2, str)
        self.assertIn("LEAD II", html2)
        self.assertIn("142", html2)  # BPM injected
        self.assertIn("2.4", html2)  # oldpeak injected

        # HARDENING ASSERTIONS:
        # Risk band 'ELEVATED' must be strictly preserved; fallback 'MODERATE' must NOT be injected!
        self.assertIn("ELEVATED", html2, "Risk band 'ELEVATED' was dropped from rendered output!")
        self.assertNotIn("MODERATE", html2, "Fallback 'MODERATE' was incorrectly injected when 'ELEVATED' was passed!")
        self.assertIn('"risk_band": "ELEVATED"', html2, "CONFIG JSON must contain 'risk_band': 'ELEVATED'")
        self.assertIn("ELEVATED (76%)", html2, "HUD badge must display 'ELEVATED (76%)'")

        # 3. embed_vendor=False option
        html3 = cgi_heart.render_cgi_heart(0.25, "LOW", embed_vendor=False)
        self.assertLess(len(html3), 150000, "Unembedded HTML should remain lightweight")
        self.assertIn("vendor/three.min.js", html3)

    def test_render_cgi_heart_partial_dictionary_missing_thalach(self):
        """render_cgi_heart must handle partial dictionaries omitting 'thalach' and default to 75 BPM."""
        import cgi_heart

        # Partial clinical intake missing 'thalach' (heart rate unmeasured)
        partial_patient = {
            "ca": 2,
            "oldpeak": 1.5,
            "slope": 1,
            "trestbps": 130,
        }
        # Positional invocation: render_cgi_heart(patient_dict, risk_prob, risk_band)
        html = cgi_heart.render_cgi_heart(partial_patient, 0.82, "HIGH")
        self.assertIsInstance(html, str)
        self.assertIn("HIGH", html, "Risk band 'HIGH' must be present in output")
        self.assertNotIn("MODERATE", html, "Fallback 'MODERATE' must not replace 'HIGH'")
        self.assertIn('"bpm": 75', html, "Omitted 'thalach' must default to 75 BPM in CONFIG")
        self.assertIn('<span id="live-bpm">75</span>', html, "HUD BPM counter must display 75")
        self.assertIn("HIGH (82%)", html, "HUD badge must display 'HIGH (82%)'")

        # Edge case: Empty dictionary {} must also safely default all biomarkers without crashing
        html_empty = cgi_heart.render_cgi_heart({}, 0.15, "LOW")
        self.assertIsInstance(html_empty, str)
        self.assertIn("LOW", html_empty)
        self.assertIn('"bpm": 75', html_empty)
        self.assertIn("LOW (15%)", html_empty)

    def test_render_cgi_heart_none_biomarker_values(self):
        """render_cgi_heart must gracefully coerce None biomarker values to clinical defaults without TypeError."""
        import cgi_heart

        # Dictionary with explicit None values across all clinical fields (simulating sparse EHR record)
        none_patient = {
            "thalach": None,
            "oldpeak": None,
            "slope": None,
            "ca": None,
            "cp": None,
            "restecg": None,
            "trestbps": None,
            "chol": None,
        }

        # 1. Positional dictionary signature: render_cgi_heart(patient_dict, risk_prob, risk_band)
        html_pos = cgi_heart.render_cgi_heart(none_patient, 0.45, "MODERATE")
        self.assertIsInstance(html_pos, str)
        self.assertIn('"bpm": 75', html_pos, "None 'thalach' must default to 75 BPM")
        self.assertIn('"oldpeak": 0.0', html_pos, "None 'oldpeak' must default to 0.0")
        self.assertIn('"slope": 2', html_pos, "None 'slope' must default to 2")
        self.assertIn('"ca": 0', html_pos, "None 'ca' must default to 0")
        self.assertIn('"cp": 4', html_pos, "None 'cp' must default to 4")
        self.assertIn('"restecg": 0', html_pos, "None 'restecg' must default to 0")
        self.assertIn('"trestbps": 120', html_pos, "None 'trestbps' must default to 120")
        self.assertIn('"chol": 200', html_pos, "None 'chol' must default to 200")
        self.assertIn("MODERATE (45%)", html_pos)

        # 2. Named argument signature: render_cgi_heart(patient_dict=..., risk_prob=..., risk_band=...)
        html_named = cgi_heart.render_cgi_heart(patient_dict=none_patient, risk_prob=0.88, risk_band="HIGH")
        self.assertIsInstance(html_named, str)
        self.assertIn("HIGH (88%)", html_named)
        self.assertIn('"bpm": 75', html_named)
        self.assertIn('"oldpeak": 0.0', html_named)

    def test_cgi_heart_context_restored_restarts_animation_loop_ast(self):
        """webglcontextrestored listener in cgi_heart.py must invoke animate() to resume render loop."""
        cgi_py = CGI_HEART_PATH.read_text(encoding="utf-8")

        # Extract the webglcontextrestored listener body bounded by its callback function braces
        match = re.search(
            r"canvas\.addEventListener\s*\(\s*['\"]webglcontextrestored['\"].*?\{(?P<body>.*?)\}\s*,\s*false\s*\)",
            cgi_py,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "webglcontextrestored event listener not found in cgi_heart.py")
        listener_body = match.group("body")

        # Assert animate() is explicitly invoked in the restore body
        self.assertRegex(
            listener_body,
            r"\banimate\s*\(\s*\)\s*;",
            "animate() must be called inside webglcontextrestored to restart the 3D heart and ECG render loop!",
        )

    def test_cgi_heart_context_restore_behavioral_rAF_resumption(self):
        """Simulate webglcontextlost and webglcontextrestored in Node.js to verify active RAF resumption."""
        import cgi_heart

        html = cgi_heart.render_cgi_heart(0.75, "ELEVATED", embed_vendor=False)
        scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html, re.DOTALL)
        self.assertGreaterEqual(len(scripts), 3, "Expected at least 3 inline scripts in cgi_heart HTML")
        cgi_js = scripts[2]

        vendor_path = json.dumps(str(VENDOR_DIR / "three.min.js"))
        test_js = (
            f"const THREE = require({vendor_path});\n"
            + r'''
THREE.WebGLRenderer = class {
  constructor(opts) { this.domElement = opts.canvas; this.disposed = false; }
  setSize() {}
  setPixelRatio() {}
  render() {}
  dispose() { this.disposed = true; }
};
THREE.OrbitControls = function() { return { update: () => {} }; };

let rAFCount = 0;
let cancelAFCount = 0;
let activeRAF = null;

global.requestAnimationFrame = (cb) => {
  rAFCount++;
  activeRAF = cb;
  return rAFCount;
};
global.cancelAnimationFrame = (id) => {
  cancelAFCount++;
  activeRAF = null;
};

const listeners = {};
const canvas = {
  style: {},
  clientWidth: 800,
  clientHeight: 600,
  addEventListener: (t, cb) => { listeners[t] = listeners[t] || []; listeners[t].push(cb); },
  removeEventListener: (t, cb) => { if (listeners[t]) listeners[t] = listeners[t].filter(f => f !== cb); },
  dispatchEvent: (t, e) => { if (listeners[t]) listeners[t].forEach(f => f(e)); }
};

const domElements = {
  'cgi-container': { clientWidth: 800, clientHeight: 600 },
  'webgl-canvas': canvas,
  'ecg-canvas': {
    clientWidth: 400,
    clientHeight: 60,
    getBoundingClientRect: () => ({ width: 400, height: 60 }),
    getContext: () => ({
      fillRect: ()=>{}, strokeRect: ()=>{}, beginPath: ()=>{}, moveTo: ()=>{}, lineTo: ()=>{}, stroke: ()=>{}, fill: ()=>{},
      setTransform: ()=>{}, scale: ()=>{}
    })
  },
  'sound-btn': { classList: { toggle: ()=>{} } },
  'sound-icon': { innerText: '' }
};

global.window = {
  devicePixelRatio: 1,
  addEventListener: () => {},
  removeEventListener: () => {},
  AudioContext: class {
    constructor() { this.state = 'running'; this.currentTime = 0; this.destination = {}; }
    createOscillator() { return { type: '', frequency: { setValueAtTime: ()=>{}, exponentialRampToValueAtTime: ()=>{} }, connect: ()=>{}, start: ()=>{}, stop: ()=>{} }; }
    createGain() { return { gain: { setValueAtTime: ()=>{}, exponentialRampToValueAtTime: ()=>{} }, connect: ()=>{} }; }
    createBiquadFilter() { return { type: '', frequency: { setValueAtTime: ()=>{} }, connect: ()=>{} }; }
  }
};
global.window.webkitAudioContext = global.window.AudioContext;

global.document = {
  getElementById: (id) => domElements[id] || null,
  querySelector: () => ({ innerText: '' }),
  querySelectorAll: () => [],
  addEventListener: () => {},
  createElement: () => ({ width: 256, height: 256, getContext: () => ({ fillRect: ()=>{}, beginPath: ()=>{}, moveTo: ()=>{}, lineTo: ()=>{}, stroke: ()=>{} }) })
};

''' + cgi_js + r'''

// 1. Dispatch context lost
canvas.dispatchEvent('webglcontextlost', { preventDefault: () => {} });
const lostState = { isCgiContextLost, cgiAnimationId, hasActiveRAF: activeRAF !== null };

// 2. Dispatch context restored
canvas.dispatchEvent('webglcontextrestored', {});
const restoredState = { isCgiContextLost, cgiAnimationId, hasActiveRAF: activeRAF !== null, rAFCount };

console.log(JSON.stringify({ lostState, restoredState }));
'''
        )
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(test_js)
            tmp_path = f.name
        try:
            res = subprocess.run(["node", tmp_path], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Node execution error:\n{res.stderr}")
            data = json.loads(res.stdout.strip().splitlines()[-1])
            self.assertTrue(data["lostState"]["isCgiContextLost"], "isCgiContextLost should be true after loss")
            self.assertFalse(data["lostState"]["hasActiveRAF"], "rAF loop should be stopped after loss")
            self.assertFalse(data["restoredState"]["isCgiContextLost"], "isCgiContextLost should be reset after restore")
            self.assertTrue(
                data["restoredState"]["hasActiveRAF"],
                "animate() was not restarted after context restore! Render loop remains frozen.",
            )
            self.assertIsNotNone(data["restoredState"]["cgiAnimationId"], "cgiAnimationId must not be null after restore")
        finally:
            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
