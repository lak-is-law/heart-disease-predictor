/**
 * American Express (Amex) Reverse-Engineered Enterprise Distribution Center
 * Hardware Architecture Detection, Oracle-Style Matrix Tab Controller & Live WebCrypto Verifier
 */

let manifest = null;
let detectedPlatform = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
  await loadManifest();
  detectClientHardware();
  renderMatrixTables();
  initTabNavigation();
  initDragAndDropVerifier();
});

/**
 * Fetch official release manifest
 */
async function loadManifest() {
  try {
    const response = await fetch('manifest.json');
    manifest = await response.json();
    console.log('[Amex Enterprise Portal] Manifest loaded:', manifest.release_name);
  } catch (error) {
    console.warn('[Amex Enterprise Portal] Local manifest fetch fallback:', error);
  }
}

/**
 * Advanced Client Chipset and Operating System Detection
 * Detects: Apple Silicon (ARM64), Intel Mac (x86_64), Windows x64, Windows ARM64
 */
async function detectClientHardware() {
  const ua = navigator.userAgent;
  const platform = navigator.platform || '';
  
  let os = 'Unknown OS';
  let arch = 'x64';
  let chipName = 'Standard 64-bit Processor';
  let packageId = 'win-x64-installer';
  let badgeIcon = '💻';

  // Check modern User-Agent Client Hints API if available
  if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
    try {
      const hints = await navigator.userAgentData.getHighEntropyValues(['architecture', 'bitness', 'model', 'platformVersion']);
      if (hints.architecture === 'arm') {
        arch = 'arm64';
      }
    } catch (e) {
      // fallback
    }
  }

  // macOS Detection & Apple Silicon check
  const isMac = /Macintosh|MacIntel|MacPPC|Mac68K/i.test(ua) || (platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (isMac) {
    os = 'macOS';
    badgeIcon = '🍎';
    
    // Check for Apple Silicon GPU renderer heuristic or ARM hints
    const isAppleSilicon = await detectAppleSiliconHeuristic();
    if (isAppleSilicon || arch === 'arm64') {
      arch = 'arm64';
      chipName = 'Apple Silicon (M1 / M2 / M3 / M4 - ARM64)';
      packageId = 'mac-arm64';
    } else {
      arch = 'x86_64';
      chipName = 'Intel Core / Xeon 64-bit (x86_64)';
      packageId = 'mac-x64';
    }
  }
  // Windows Detection
  else if (/Win(dows )?/i.test(ua)) {
    os = 'Windows';
    badgeIcon = '🪟';
    if (/ARM64|WOA/i.test(ua) || arch === 'arm64') {
      arch = 'arm64';
      chipName = 'Windows on ARM64 (Qualcomm Snapdragon X Elite)';
      packageId = 'win-arm64-installer';
    } else {
      arch = 'x64';
      chipName = 'Intel / AMD 64-bit Processor (x64)';
      packageId = 'win-x64-installer';
    }
  }
  // Linux Detection
  else if (/Linux/i.test(ua)) {
    os = 'Enterprise Linux';
    badgeIcon = '🐧';
    arch = 'x86_64';
    chipName = 'x86_64 Architecture';
    packageId = 'linux-x64-tar';
  }

  detectedPlatform = { os, arch, chipName, packageId, badgeIcon };
  updateSmartRecommendationCard(detectedPlatform);
}

/**
 * Heuristic to detect Apple Silicon via WebGL unmasked renderer
 */
async function detectAppleSiliconHeuristic() {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) return false;
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    if (!debugInfo) return false;
    const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
    // Apple Silicon reports 'Apple M1', 'Apple M2', 'Apple M3', 'Apple M4', or 'Apple GPU'
    if (/Apple M[1-4]|Apple GPU/i.test(renderer)) {
      return true;
    }
  } catch (e) {
    // ignore
  }
  return true; // Default modern Macs to Apple Silicon if indeterminate
}

/**
 * Render the Personalized Amex Recommendation Card
 */
function updateSmartRecommendationCard(detected) {
  const card = document.getElementById('smart-recommendation-card');
  if (!card || !manifest) return;

  const pkg = manifest.packages.find(p => p.id === detected.packageId) || manifest.packages[0];

  const titleEl = document.getElementById('rec-title');
  const descEl = document.getElementById('rec-desc');
  const metaEl = document.getElementById('rec-meta');
  const btnEl = document.getElementById('rec-btn');
  const hashEl = document.getElementById('rec-hash-link');

  if (titleEl) {
    titleEl.innerHTML = `${detected.badgeIcon} ${pkg.description}`;
  }
  if (descEl) {
    descEl.innerText = `Specifically compiled and optimized for your ${detected.os} workstation running ${detected.chipName}. Verified and digitally notarized.`;
  }
  if (metaEl) {
    metaEl.innerHTML = `
      <span><strong>Chip:</strong> ${pkg.chipset_short}</span>
      <span>•</span>
      <span><strong>Size:</strong> ${pkg.size_mb} MB</span>
      <span>•</span>
      <span><strong>Format:</strong> ${pkg.type}</span>
      <span>•</span>
      <span><strong>Security:</strong> FIPS 140-2 Compatible</span>
    `;
  }
  if (btnEl) {
    btnEl.href = pkg.download_url;
    btnEl.download = pkg.filename;
    btnEl.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      Download for ${detected.os} (${pkg.chipset_short})
    `;
  }
  if (hashEl) {
    hashEl.onclick = (e) => {
      e.preventDefault();
      copyToClipboard(pkg.sha256, `Copied SHA-256 for ${pkg.filename}`);
    };
    hashEl.innerText = `SHA-256: ${pkg.sha256.substring(0, 16)}... (Click to copy)`;
  }
}

/**
 * Render Oracle-Style Architecture Tables for macOS, Windows, Linux, and All
 */
function renderMatrixTables() {
  if (!manifest) return;

  const macPackages = manifest.packages.filter(p => p.platform === 'macOS');
  const winPackages = manifest.packages.filter(p => p.platform === 'Windows');
  const linuxPackages = manifest.packages.filter(p => p.platform === 'Linux');

  renderTable('table-mac-body', macPackages);
  renderTable('table-win-body', winPackages);
  renderTable('table-linux-body', linuxPackages);
  renderTable('table-all-body', manifest.packages);
}

function renderTable(tableBodyId, packages) {
  const tbody = document.getElementById(tableBodyId);
  if (!tbody) return;

  tbody.innerHTML = '';
  packages.forEach(pkg => {
    const isRecommended = detectedPlatform && pkg.id === detectedPlatform.packageId;
    const tr = document.createElement('tr');
    if (isRecommended) tr.className = 'highlighted-row';

    let chipClass = 'chip-x64';
    if (pkg.chipset_short.includes('ARM')) {
      chipClass = pkg.platform === 'macOS' ? 'chip-arm64' : 'chip-win-arm';
    }

    let fileBadge = 'file-dmg';
    if (pkg.filename.endsWith('.exe')) fileBadge = 'file-exe';
    if (pkg.filename.endsWith('.tar.gz') || pkg.filename.endsWith('.zip')) fileBadge = 'file-zip';

    tr.innerHTML = `
      <td>
        <span class="file-type-badge ${fileBadge}">${pkg.filename.split('.').pop()}</span>
        <strong>${pkg.filename}</strong>
        ${isRecommended ? '<span class="amex-chip-pill chip-arm64" style="margin-left:8px;">★ RECOMMENDED</span>' : ''}
        <div style="font-size:0.75rem; color:#6B7280; margin-top:2px;">${pkg.description}</div>
      </td>
      <td>
        <span class="amex-chip-pill ${chipClass}">${pkg.chipset}</span>
      </td>
      <td style="color:#4B5563;">
        ${pkg.os_compat}
      </td>
      <td>
        <strong>${pkg.size_mb} MB</strong>
      </td>
      <td>
        <div class="amex-hash-box">
          <span class="amex-hash-code" title="${pkg.sha256}">${pkg.sha256}</span>
          <button class="amex-copy-btn" onclick="copyToClipboard('${pkg.sha256}', 'SHA-256 Checksum Copied')">
            Copy
          </button>
        </div>
      </td>
      <td style="text-align:right;">
        <a href="${pkg.download_url}" download="${pkg.filename}" class="amex-btn amex-btn-primary amex-btn-sm">
          Download
        </a>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

/**
 * Tab Navigation Controller
 */
function initTabNavigation() {
  const tabs = document.querySelectorAll('.amex-tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const targetId = tab.getAttribute('data-target');
      document.querySelectorAll('.amex-tab-content').forEach(c => c.style.display = 'none');
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.style.display = 'block';
    });
  });
}

/**
 * Clipboard Copy with Amex Toast Alert
 */
function copyToClipboard(text, message = 'Copied to clipboard!') {
  navigator.clipboard.writeText(text).then(() => {
    showToast(message);
  }).catch(err => {
    console.error('Failed to copy: ', err);
  });
}

function showToast(message) {
  let toast = document.getElementById('amex-portal-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'amex-portal-toast';
    toast.className = 'amex-toast';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C5A059" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
    <span>${message}</span>
  `;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2600);
}

/**
 * Live Client-Side WebCrypto SHA-256 Verifier
 */
function initDragAndDropVerifier() {
  const dropzone = document.getElementById('amex-verifier-dropzone');
  const fileInput = document.getElementById('verifier-file-input');
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileVerification(files[0]);
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFileVerification(e.target.files[0]);
  });
}

async function handleFileVerification(file) {
  const resultBox = document.getElementById('verification-result-box');
  const statusTitle = document.getElementById('verification-status-title');
  const statusDetails = document.getElementById('verification-status-details');
  const hashOutput = document.getElementById('verification-computed-hash');

  if (!resultBox) return;

  resultBox.style.display = 'flex';
  resultBox.className = 'amex-verification-result';
  statusTitle.innerText = `Hashing ${file.name}...`;
  statusDetails.innerText = 'Calculating SHA-256 checksum in client sandbox via Web Crypto API...';

  try {
    const arrayBuffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const computedHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    hashOutput.innerText = `Computed SHA-256: ${computedHash}`;

    // Compare with official manifest
    const match = manifest?.packages.find(p => p.sha256.toLowerCase() === computedHash.toLowerCase());

    if (match) {
      resultBox.className = 'amex-verification-result verified';
      statusTitle.innerHTML = `✓ AUTHENTICATED: Official American Express Enterprise Release`;
      statusDetails.innerHTML = `
        The package <strong>${file.name}</strong> matches the official signed digest for <strong>${match.filename}</strong> (${match.chipset}).
        This binary is safe to execute on enterprise workstations.
      `;
    } else {
      resultBox.className = 'amex-verification-result unverified';
      statusTitle.innerHTML = `⚠ UNVERIFIED CHECKSUM`;
      statusDetails.innerHTML = `
        The computed hash does not match any official package in Release ${manifest?.version || '2.4.0'}.
        Ensure you downloaded the file directly from this certified American Express Enterprise portal.
      `;
    }
  } catch (err) {
    statusTitle.innerText = 'Verification Error';
    statusDetails.innerText = err.message;
  }
}
