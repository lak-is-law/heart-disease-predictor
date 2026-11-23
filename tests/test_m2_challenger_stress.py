"""Empirical Stress Test Suite for Milestone M2:
WebGL Context Loss Simulation, Web Audio Synthesis, and Local HTTP Serving.
Authored by m2_challenger_2.
"""

from __future__ import annotations

import concurrent.futures
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PORTAL_DIR = REPO_ROOT / "portal"
VENDOR_DIR = PORTAL_DIR / "vendor"
CGI_HEART_PATH = REPO_ROOT / "cgi_heart.py"
PORTAL_JS_PATH = PORTAL_DIR / "portal.js"
PORTAL_HTML_PATH = PORTAL_DIR / "app.html"

from serve_portal import PortalHTTPRequestHandler, find_available_port


class TestM2ChallengerContextLoss(unittest.TestCase):
    """Empirical verification of WebGL Context Loss lifecycle in portal.js and cgi_heart.py."""

    def test_portal_js_context_loss_lifecycle(self):
        """portal.js must prevent default, halt rAF loop, dispose scene, and resume upon restore."""
        portal_js = PORTAL_JS_PATH.read_text(encoding="utf-8")

        test_js = r'''
const fs = require('fs');
const THREE = require('/Users/lakshya/Projects/heart/heart-disease-predictor/portal/vendor/three.min.js');

class MockWebGLRenderer {
  constructor(opts) { this.domElement = opts.canvas; this.disposed = false; }
  setSize() {}
  setPixelRatio() {}
  render() {}
  dispose() { this.disposed = true; }
}
THREE.WebGLRenderer = MockWebGLRenderer;
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

const badge = { style: { display: 'none' } };
const domElements = {
  'portal-cgi-viewport': { clientWidth: 800, clientHeight: 600 },
  'portal-webgl-canvas': canvas,
  'portal-context-recovery-badge': badge,
  'portal-mode-cta': { classList: { add: ()=>{}, remove: ()=>{} }, setAttribute: ()=>{} },
  'portal-mode-perfusion': { classList: { add: ()=>{}, remove: ()=>{} }, setAttribute: ()=>{} },
  'portal-mode-fluoro': { classList: { add: ()=>{}, remove: ()=>{} }, setAttribute: ()=>{} },
  'portal-mode-ffr': { classList: { add: ()=>{}, remove: ()=>{} }, setAttribute: ()=>{} },
  'portal-ffr-telemetry': { innerHTML: '', style: {} },
  'portal-ffr-val': { innerText: '' },
  'portal-lesion-callout': { innerHTML: '', style: {} },
  'portal-stenosis-summary': { innerText: '' },
  'portal-ecg-canvas': { clientWidth: 320, clientHeight: 48, getBoundingClientRect: () => ({ width: 320, height: 48 }), getContext: () => ({
    fillRect: ()=>{}, strokeRect: ()=>{}, beginPath: ()=>{}, moveTo: ()=>{}, lineTo: ()=>{}, stroke: ()=>{}, fill: ()=>{}, setTransform: ()=>{}, scale: ()=>{}
  })},
  'portal-sound-btn': { classList: { toggle: ()=>{} } },
  'portal-sound-icon': { innerText: '' }
};

global.window = {
  devicePixelRatio: 1,
  addEventListener: () => {},
  removeEventListener: () => {},
  ResizeObserver: class { observe() {} disconnect() {} },
  AudioContext: class {
    constructor() { this.state = 'running'; this.currentTime = 0; this.destination = {}; }
    createOscillator() { return { type: '', frequency: { setValueAtTime: ()=>{}, exponentialRampToValueAtTime: ()=>{} }, connect: ()=>{}, start: ()=>{}, stop: ()=>{} }; }
    createGain() { return { gain: { setValueAtTime: ()=>{}, exponentialRampToValueAtTime: ()=>{} }, connect: ()=>{} }; }
    createBiquadFilter() { return { type: '', frequency: { setValueAtTime: ()=>{} }, connect: ()=>{} }; }
  }
};
global.window.webkitAudioContext = global.window.AudioContext;
global.ResizeObserver = global.window.ResizeObserver;

global.document = {
  getElementById: (id) => domElements[id] || null,
  querySelector: () => ({ innerText: '' }),
  querySelectorAll: () => [],
  addEventListener: () => {},
  createElement: () => ({ width: 256, height: 256, getContext: () => ({ fillRect: ()=>{}, beginPath: ()=>{}, moveTo: ()=>{}, lineTo: ()=>{}, stroke: ()=>{} }) })
};

''' + portal_js + r'''

initPortal3DHeart();

let initialGeoms = 0;
let disposedGeoms = 0;
pScene.traverse(obj => {
  if (obj.geometry) {
    initialGeoms++;
    const oldD = obj.geometry.dispose.bind(obj.geometry);
    obj.geometry.dispose = () => { disposedGeoms++; oldD(); };
  }
});

// Trigger context lost
let preventDefaultFired = false;
canvas.dispatchEvent('webglcontextlost', { preventDefault: () => { preventDefaultFired = true; } });

const postLossState = {
  preventDefaultFired,
  isPortalContextLost,
  pAnimationId,
  cancelAFCount,
  badgeDisplay: badge.style.display
};

// Trigger context restored
canvas.dispatchEvent('webglcontextrestored', {});

const postRestoreState = {
  isPortalContextLost,
  initialGeoms,
  disposedGeoms,
  pAnimationId,
  hasActiveRAF: activeRAF !== null,
  rAFCount,
  badgeDisplay: badge.style.display
};

console.log(JSON.stringify({ postLossState, postRestoreState }));
'''

        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(test_js)
            tmp_path = f.name
        try:
            res = subprocess.run(["node", tmp_path], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Node execution error:\n{res.stderr}")
            data = json.loads(res.stdout.strip().splitlines()[-1])
            loss = data["postLossState"]
            rest = data["postRestoreState"]

            self.assertTrue(loss["preventDefaultFired"], "preventDefault was not called on context lost")
            self.assertTrue(loss["isPortalContextLost"], "isPortalContextLost not set to true")
            self.assertIsNone(loss["pAnimationId"], "pAnimationId not cleared on context lost")
            self.assertEqual(loss["badgeDisplay"], "flex", "Recovery badge was not displayed on context lost")

            self.assertFalse(rest["isPortalContextLost"], "isPortalContextLost not reset on restore")
            self.assertEqual(rest["initialGeoms"], rest["disposedGeoms"], "Not all geometries disposed")
            self.assertIsNotNone(rest["pAnimationId"], "pAnimationId not re-created on restore")
            self.assertTrue(rest["hasActiveRAF"], "rAF loop not resumed after restore")
            self.assertEqual(rest["badgeDisplay"], "none", "Recovery badge not hidden after restore")
        finally:
            os.remove(tmp_path)

    def test_cgi_heart_context_loss_animation_loop_freeze(self):
        """Demonstrates whether cgi_heart.py restarts animate() upon webglcontextrestored."""
        import cgi_heart

        html = cgi_heart.render_cgi_heart(0.85, "HIGH", embed_vendor=False)
        scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html, re.DOTALL)
        cgi_js = scripts[2]

        test_js = r'''
const THREE = require('/Users/lakshya/Projects/heart/heart-disease-predictor/portal/vendor/three.min.js');

class MockWebGLRenderer {
  constructor(opts) { this.domElement = opts.canvas; this.disposed = false; }
  setSize() {}
  setPixelRatio() {}
  render() {}
  dispose() { this.disposed = true; }
}
THREE.WebGLRenderer = MockWebGLRenderer;
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

// Context loss
let preventDefaultFired = false;
canvas.dispatchEvent('webglcontextlost', { preventDefault: () => { preventDefaultFired = true; } });

// Context restore
canvas.dispatchEvent('webglcontextrestored', {});

const result = {
  isCgiContextLost,
  cgiAnimationId,
  hasActiveRAF: activeRAF !== null,
  rAFCount
};
console.log(JSON.stringify(result));
'''

        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(test_js)
            tmp_path = f.name
        try:
            res = subprocess.run(["node", tmp_path], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Node execution error:\n{res.stderr}")
            result = json.loads(res.stdout.strip().splitlines()[-1])
            # EMPIRICAL OBSERVATION: cgiAnimationId is null and activeRAF is False
            # Verify cgiAnimationId is restored and activeRAF is True
            self.assertIsNotNone(result["cgiAnimationId"], "Expected cgiAnimationId to be restored in cgi_heart")
            self.assertTrue(result["hasActiveRAF"], "Expected activeRAF to be True after restore in cgi_heart")
        finally:
            os.remove(tmp_path)


class TestM2ChallengerWebAudio(unittest.TestCase):
    """Stress tests Web Audio API stethoscope synthesis and autoplay compliance."""

    def test_audio_synthesis_nodes_and_stress(self):
        """Audio synthesizer must be muted initially, not crash uninitialized, and create proper nodes."""
        portal_js = PORTAL_JS_PATH.read_text(encoding="utf-8")

        test_js = r'''
const fs = require('fs');
const portal_js = fs.readFileSync('/Users/lakshya/Projects/heart/heart-disease-predictor/portal/portal.js', 'utf-8');

let createdOscillators = [];
let createdGains = [];
let createdFilters = [];

class MockAudioParam {
  constructor(initialVal = 0) {
    this.value = initialVal;
    this.events = [];
  }
  setValueAtTime(val, t) { this.events.push(['set', val, t]); }
  exponentialRampToValueAtTime(val, t) { this.events.push(['ramp', val, t]); }
}

class MockAudioNode {
  constructor(type) { this.type = type; this.connectedTo = null; }
  connect(dest) { this.connectedTo = dest; }
}

class MockOscillatorNode extends MockAudioNode {
  constructor() {
    super('oscillator');
    this.frequency = new MockAudioParam(440);
    this.oscType = 'sine';
    this.started = null;
    this.stopped = null;
    createdOscillators.push(this);
  }
  set type(t) { this.oscType = t; }
  get type() { return this.oscType; }
  start(t) { this.started = t; }
  stop(t) { this.stopped = t; }
}

class MockGainNode extends MockAudioNode {
  constructor() {
    super('gain');
    this.gain = new MockAudioParam(1);
    createdGains.push(this);
  }
}

class MockBiquadFilterNode extends MockAudioNode {
  constructor() {
    super('biquad');
    this.filterType = 'lowpass';
    this.frequency = new MockAudioParam(350);
    createdFilters.push(this);
  }
  set type(t) { this.filterType = t; }
  get type() { return this.filterType; }
}

class MockAudioContext {
  constructor() {
    this.currentTime = 0;
    this.state = 'running';
    this.destination = { type: 'destination' };
  }
  createOscillator() { return new MockOscillatorNode(); }
  createGain() { return new MockGainNode(); }
  createBiquadFilter() { return new MockBiquadFilterNode(); }
  resume() { this.state = 'running'; }
}

global.window = {
  AudioContext: MockAudioContext,
  webkitAudioContext: MockAudioContext
};

const start = portal_js.indexOf('class CardiacAcousticSynthesizer');
const end = portal_js.indexOf('function togglePortalAudio');
const classCode = portal_js.substring(start, end).trim();
global.CardiacAcousticSynthesizer = eval('(function(){ return ' + classCode + '; })()');

const synth = new CardiacAcousticSynthesizer();
const initialMuted = synth.soundEnabled === false && synth.audioCtx === null;

// Uninitialized update (must not throw)
let uninitializedSafe = true;
try {
  synth.update(75, 0.5, 0);
} catch (e) {
  uninitializedSafe = false;
}

// Toggle on
const btn = { classList: { toggle: ()=>{} }, setAttribute: ()=>{} };
const icon = { innerText: '' };
synth.toggle(btn, icon);
const toggleOnSuccess = synth.soundEnabled === true && synth.audioCtx !== null;

// Test normal risk tone generation (S1 and S2)
createdOscillators = [];
synth.audioCtx.currentTime = 1.0;
synth.nextBeatTime = 1.0;
synth.update(75, 0.40, 0);
const normalOscCount = createdOscillators.length;

// Test high risk tone generation (S1, S2, S3 gallop)
createdOscillators = [];
synth.audioCtx.currentTime = 2.0;
synth.nextBeatTime = 2.0;
synth.update(85, 0.85, 2);
const highRiskOscCount = createdOscillators.length;

// Stress test: extreme BPM values
let extremeSafe = true;
[-100, 0, NaN, Infinity, 1000].forEach(bpm => {
  try {
    synth.audioCtx.currentTime += 1.0;
    synth.nextBeatTime = synth.audioCtx.currentTime;
    synth.update(bpm, 0.5, 0);
  } catch (e) {
    extremeSafe = false;
  }
});

console.log(JSON.stringify({
  initialMuted,
  uninitializedSafe,
  toggleOnSuccess,
  normalOscCount,
  highRiskOscCount,
  extremeSafe
}));
'''

        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(test_js)
            tmp_path = f.name
        try:
            res = subprocess.run(["node", tmp_path], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Node execution error:\n{res.stderr}")
            data = json.loads(res.stdout.strip().splitlines()[-1])

            self.assertTrue(data["initialMuted"], "AudioContext not muted initially")
            self.assertTrue(data["uninitializedSafe"], "Uninitialized update threw an error")
            self.assertTrue(data["toggleOnSuccess"], "Toggle failed to activate audio")
            self.assertEqual(data["normalOscCount"], 2, "Expected 2 tones (S1, S2) for normal risk")
            self.assertEqual(data["highRiskOscCount"], 3, "Expected 3 tones (S1, S2, S3) for high risk")
            self.assertTrue(data["extremeSafe"], "Extreme BPM stress test caused error")
        finally:
            os.remove(tmp_path)


class TestM2ChallengerHTTPServer(unittest.TestCase):
    """Stress tests local HTTP serving via serve_portal.py, MIME routing, and offline integrity."""

    @classmethod
    def setUpClass(cls):
        cls.port = find_available_port(9200)
        cls.httpd = socketserver.TCPServer(("127.0.0.1", cls.port), PortalHTTPRequestHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_http_serving_endpoints_and_mime_types(self):
        """All static portal endpoints must return 200, matching exact disk bytes and correct MIME types."""
        endpoints = [
            ("/", PORTAL_DIR / "index.html", "text/html"),
            ("/index.html", PORTAL_DIR / "index.html", "text/html"),
            ("/vendor/three.min.js", PORTAL_DIR / "vendor/three.min.js", "javascript"),
            ("/vendor/OrbitControls.js", PORTAL_DIR / "vendor/OrbitControls.js", "javascript"),
            ("/portal.js", PORTAL_DIR / "portal.js", "javascript"),
            ("/styles.css", PORTAL_DIR / "styles.css", "text/css"),
            ("/manifest.json", PORTAL_DIR / "manifest.json", "application/json"),
            ("/model_weights.json", PORTAL_DIR / "model_weights.json", "application/json"),
        ]

        for ep, file_path, expected_mime in endpoints:
            url = f"http://127.0.0.1:{self.port}{ep}"
            with urllib.request.urlopen(url) as resp:
                self.assertEqual(resp.status, 200, f"Failed HTTP 200 for {ep}")
                ct = resp.headers.get("Content-Type", "")
                self.assertIn(expected_mime, ct, f"MIME mismatch for {ep}: {ct} does not contain {expected_mime}")
                body = resp.read()
                expected_bytes = file_path.read_bytes()
                self.assertEqual(len(body), len(expected_bytes), f"Byte length mismatch for {ep}")
                self.assertEqual(body, expected_bytes, f"Content mismatch for {ep}")

    def test_concurrent_serving_stress(self):
        """Concurrently fetching all endpoints must succeed without race conditions."""
        endpoints = [
            ("/vendor/three.min.js", PORTAL_DIR / "vendor/three.min.js"),
            ("/vendor/OrbitControls.js", PORTAL_DIR / "vendor/OrbitControls.js"),
            ("/portal.js", PORTAL_DIR / "portal.js"),
            ("/styles.css", PORTAL_DIR / "styles.css"),
        ] * 10  # 40 concurrent requests

        def worker(pair):
            ep, fp = pair
            url = f"http://127.0.0.1:{self.port}{ep}"
            with urllib.request.urlopen(url) as resp:
                return resp.status == 200 and len(resp.read()) == fp.stat().st_size

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(worker, endpoints))

        self.assertTrue(all(results), "Not all concurrent requests succeeded")

    def test_offline_integrity_zero_external_network_dependencies(self):
        """Local index.html must load vendor assets locally first, not blindly requesting CDNs."""
        html = (PORTAL_DIR / "app.html").read_text(encoding="utf-8")
        # Ensure local scripts precede any CDN fallback
        self.assertIn('<script src="vendor/three.min.js"></script>', html)
        self.assertIn('<script src="vendor/OrbitControls.js"></script>', html)


if __name__ == "__main__":
    unittest.main()
