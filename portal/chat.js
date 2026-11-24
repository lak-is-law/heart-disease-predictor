/* CardioSense help chat. Answers questions about the site from a fixed FAQ, in English or Hindi.
   No server, no AI model: it matches keywords against the answers below. */
(function () {
  'use strict';
  var KB = [
    { id: 'what', k: ['what is', 'what does', 'about', 'cardiosense', 'kya hai', 'क्या है', 'क्या करता', 'के बारे'],
      en: 'CardioSense estimates the probability of coronary artery disease from 13 clinical values (age, sex, blood pressure, cholesterol, ECG and stress-test results and so on). It also shows a 3D heart and an ECG trace, imports lab reports and saves assessments to your account. It is a research prototype for learning.',
      hi: 'CardioSense 13 क्लिनिकल मानों (उम्र, लिंग, रक्तचाप, कोलेस्ट्रॉल, ECG और स्ट्रेस टेस्ट आदि) से कोरोनरी धमनी रोग की संभावना का अनुमान लगाता है। इसमें 3D हृदय, ECG ट्रेस, लैब रिपोर्ट इम्पोर्ट और खाते में असेसमेंट सेव करने की सुविधा भी है। यह सीखने के लिए बना शोध प्रोटोटाइप है।' },
    { id: 'device', k: ['medical device', 'diagnos', 'doctor', 'fda', 'approved', 'clinical use', 'safe to use', 'real patient', 'डॉक्टर', 'निदान', 'मेडिकल डिवाइस', 'इलाज', 'मंज़ूर', 'मंजूर'],
      en: 'No. CardioSense is not a medical device and has not been reviewed by any regulator. Do not use it to diagnose, to rule out disease or to decide treatment. See a qualified doctor for any health concern, and do not enter real patient information.',
      hi: 'नहीं। CardioSense कोई मेडिकल डिवाइस नहीं है और किसी नियामक ने इसकी समीक्षा नहीं की है। इसका उपयोग निदान, बीमारी को नकारने या इलाज तय करने के लिए न करें। स्वास्थ्य संबंधी किसी भी चिंता के लिए योग्य डॉक्टर से मिलें, और असली मरीज़ की जानकारी न डालें।' },
    { id: 'accuracy', k: ['accura', 'auc', 'reliable', 'how good', 'precision', 'validated', 'trust', 'सटीक', 'भरोसा', 'विश्वसनीय', 'कितना सही', 'एक्यूरेसी'],
      en: 'Cross-validated AUC is 0.91 (95% CI 0.87 to 0.94) with all 13 inputs and 0.84 (0.79 to 0.88) without the invasive and stress-test inputs. This comes from 303 patients at one clinic. It has not been tested at another site or prospectively, and a low estimate does not rule out disease. Details: /features#limits',
      hi: 'सभी 13 इनपुट के साथ क्रॉस-वैलिडेटेड AUC 0.91 है (95% CI 0.87 से 0.94), और इनवेसिव व स्ट्रेस-टेस्ट इनपुट के बिना 0.84 (0.79 से 0.88)। यह एक क्लिनिक के 303 मरीज़ों पर आधारित है। इसे किसी दूसरी जगह या भविष्य में परखा नहीं गया है, और कम अनुमान का मतलब यह नहीं कि बीमारी नहीं है। विवरण: /features#limits' },
    { id: 'privacy', k: ['privacy', 'data', 'secure', 'security', 'encrypt', 'store', 'safe', 'delete', 'डेटा', 'गोपनीय', 'सुरक्षित', 'एन्क्रिप्ट', 'डिलीट', 'हटा'],
      en: 'The calculator runs in your browser. If you save an assessment, its fields are encrypted on the server (AES-256-GCM) and tied to your account. You can delete any assessment, or all of them, from the dashboard. Use synthetic or de-identified data only.',
      hi: 'कैलकुलेटर आपके ब्राउज़र में चलता है। असेसमेंट सेव करने पर उसके फ़ील्ड सर्वर पर एन्क्रिप्ट (AES-256-GCM) होकर आपके खाते से जुड़ते हैं। डैशबोर्ड से आप कोई भी या सभी असेसमेंट डिलीट कर सकते हैं। केवल नकली या पहचान हटाया हुआ डेटा इस्तेमाल करें।' },
    { id: 'download', k: ['download', 'install', 'mac', 'windows', 'dmg', 'exe', 'apple silicon', 'intel', 'arm', 'platform', 'डाउनलोड', 'इंस्टॉल', 'विंडोज', 'मैक'],
      en: 'Installers are available for macOS (Apple silicon and Intel) and Windows (x64 and ARM64), or you can use the workstation in any modern browser. You need to sign in to start a download. Each installer lists a SHA-256 checksum. Go to /download. On a Mac, Apple menu > About This Mac shows your chip; on Windows, Settings > System > About shows System type.',
      hi: 'macOS (Apple silicon और Intel) और Windows (x64 और ARM64) के लिए इंस्टॉलर उपलब्ध हैं, या आप किसी भी आधुनिक ब्राउज़र में वर्कस्टेशन चला सकते हैं। डाउनलोड शुरू करने के लिए साइन इन करना होगा। हर इंस्टॉलर के साथ SHA-256 चेकसम दिया है। /download पर जाएँ। Mac में Apple मेनू > About This Mac से चिप दिखती है; Windows में Settings > System > About में System type देखें।' },
    { id: 'verify', k: ['checksum', 'sha', 'verify', 'hash', 'चेकसम', 'सत्यापित', 'वेरिफाई'],
      en: 'On /download, choose the file you downloaded. Your browser computes its SHA-256 locally (nothing is uploaded) and you can compare it with the value listed for that installer.',
      hi: '/download पर अपनी डाउनलोड की हुई फ़ाइल चुनें। आपका ब्राउज़र उसका SHA-256 स्थानीय रूप से निकालता है (कुछ अपलोड नहीं होता), और आप उसे इंस्टॉलर के सामने दिए मान से मिला सकते हैं।' },
    { id: 'account', k: ['sign up', 'signup', 'sign in', 'signin', 'login', 'log in', 'account', 'register', 'google', 'microsoft', 'password', 'chatgpt', 'खाता', 'साइन', 'लॉगिन', 'रजिस्टर', 'पासवर्ड'],
      en: 'Create an account at /signup with your email and a password of at least 12 characters, or continue with Google, Microsoft, X or ChatGPT where those options are enabled. Sign in at /signin. Signing out ends your session on the server.',
      hi: '/signup पर ईमेल और कम से कम 12 अक्षरों के पासवर्ड से खाता बनाएँ, या जहाँ सुविधा चालू हो वहाँ Google, Microsoft, X या ChatGPT से जारी रखें। /signin पर साइन इन करें। साइन आउट करने पर सर्वर पर आपका सेशन खत्म हो जाता है।' },
    { id: 'inputs', k: ['input', 'inputs', 'which values', 'what do i enter', 'fields', 'thallium', 'vessel', 'इनपुट', 'कौन से मान', 'क्या डालना', 'फ़ील्ड'],
      en: 'The 13 inputs are age, sex, chest-pain type, resting blood pressure, cholesterol, fasting glucose, resting ECG, maximum heart rate, exercise angina, ST depression, ST slope, number of vessels on fluoroscopy and the thallium result. Vessel count and thallium are required; without them no estimate is shown.',
      hi: '13 इनपुट: उम्र, लिंग, सीने के दर्द का प्रकार, आराम के समय रक्तचाप, कोलेस्ट्रॉल, फास्टिंग ग्लूकोज़, रेस्टिंग ECG, अधिकतम हृदय गति, एक्सरसाइज़ एंजाइना, ST डिप्रेशन, ST स्लोप, फ्लोरोस्कोपी में दिखी नलिकाओं की संख्या और थैलियम परिणाम। नलिकाओं की संख्या और थैलियम अनिवार्य हैं; इनके बिना अनुमान नहीं दिखता।' },
    { id: 'threshold', k: ['threshold', 'sensitivity', '0.28', 'high-sensitivity', 'flag', 'cutoff', 'थ्रेशोल्ड', 'संवेदनशीलता', 'फ्लैग'],
      en: 'Standard mode flags a case at a probability of 0.50. High-sensitivity mode flags at 0.28, which caught about 88% of cases in cross-validation but also flags many people without disease.',
      hi: 'स्टैंडर्ड मोड में संभावना 0.50 होने पर केस फ्लैग होता है। हाई-सेंसिटिविटी मोड 0.28 पर फ्लैग करता है, जिसने क्रॉस-वैलिडेशन में लगभग 88% केस पकड़े, पर बिना बीमारी वाले कई लोगों को भी फ्लैग करता है।' },
    { id: 'import', k: ['import', 'upload', 'lab report', 'csv', 'json', 'hl7', 'report', 'इम्पोर्ट', 'अपलोड', 'लैब', 'रिपोर्ट'],
      en: 'In the workstation you can drop in a lab report as CSV, JSON, HL7 v2 or plain-text notes and the matching fields are filled. Sample files are included. Always check every imported value.',
      hi: 'वर्कस्टेशन में लैब रिपोर्ट CSV, JSON, HL7 v2 या सादे टेक्स्ट नोट्स के रूप में डालें, मिलते-जुलते फ़ील्ड अपने आप भर जाएँगे। नमूना फ़ाइलें साथ में हैं। हर इम्पोर्ट किए मान को ज़रूर जाँचें।' },
    { id: 'heart', k: ['3d', 'heart model', 'ecg', 'animation', 'chamber', 'rotate', 'हृदय', 'दिल', 'ईसीजी', 'चैंबर'],
      en: 'The 3D heart has four chambers and turns and opens along the four-chamber plane as you scroll. The ECG trace responds to your inputs. Both are teaching aids, not images or measurements of a patient.',
      hi: '3D हृदय में चार कक्ष हैं और स्क्रॉल करने पर वह घूमता और चार-कक्ष तल पर खुलता है। ECG ट्रेस आपके इनपुट के अनुसार बदलता है। दोनों सिखाने के साधन हैं, किसी मरीज़ की तस्वीर या माप नहीं।' },
    { id: 'reviews', k: ['review', 'rating', 'testimonial', 'feedback', 'रिव्यू', 'समीक्षा', 'रेटिंग'],
      en: 'Reviews on the home page are written by signed-in users. Sign in to add one; it shows your first name and last initial, and submitting again edits it.',
      hi: 'होम पेज की समीक्षाएँ साइन-इन किए हुए उपयोगकर्ता लिखते हैं। जोड़ने के लिए साइन इन करें; यह आपका पहला नाम और अंतिम नाम का पहला अक्षर दिखाती है, और दोबारा भेजने पर बदल जाती है।' },
    { id: 'contact', k: ['contact', 'support', 'bug', 'issue', 'problem', 'not working', 'error', 'report', 'संपर्क', 'सहायता', 'मदद', 'बग', 'समस्या', 'दिक्कत'],
      en: 'To report a problem, use the Report a bug link in the footer (/report). Describe what happened and which page you were on.',
      hi: 'समस्या बताने के लिए फ़ुटर में "Report a bug" लिंक (/report) का उपयोग करें। बताइए क्या हुआ और आप किस पेज पर थे।' },
    { id: 'hello', k: ['hello', 'hi', 'hey', 'namaste', 'thanks', 'thank', 'नमस्ते', 'हेलो', 'धन्यवाद', 'शुक्रिया'],
      en: 'Hello. Ask me about what CardioSense does, accuracy, privacy, downloads or accounts.', hi: 'नमस्ते। CardioSense क्या करता है, सटीकता, गोपनीयता, डाउनलोड या खाते के बारे में पूछिए।' }
  ];
  var EMERGENCY = ['chest pain', 'heart attack', 'emergency', 'cant breathe', "can't breathe", 'short of breath', 'fainting', 'seene mein dard', 'सीने में दर्द', 'सीने मे दर्द', 'दिल का दौरा', 'हार्ट अटैक', 'सांस नहीं', 'आपातकाल', 'बेहोश'];
  var MEDQ = ['do i have', 'am i at risk', 'should i take', 'medicine', 'medication', 'treatment', 'क्या मुझे', 'दवा', 'दवाई', 'मुझे बीमारी'];
  var T = {
    en: { title: 'CardioSense help', ph: 'Ask a question', send: 'Send', open: 'Help', close: 'Close',
      hi: 'Hi. I can answer questions about CardioSense in English or Hindi. I cannot give medical advice.',
      note: 'Automated answers from the site FAQ. Not medical advice.',
      none: 'I could not find an answer to that. Try one of the questions below, or report a problem at /report',
      emerg: 'If you or someone else has chest pain, trouble breathing or fainting, call your local emergency number now (112 in India) or go to the nearest hospital. This site cannot help in an emergency.',
      med: 'I cannot give medical advice or say whether you have a condition. CardioSense is a learning tool, not a medical device. Please speak to a qualified doctor.',
      chips: [['what', 'What is CardioSense?'], ['device', 'Is it a medical device?'], ['accuracy', 'How accurate is it?'], ['privacy', 'What happens to my data?'], ['download', 'How do I download it?'], ['account', 'How do I sign up?']] },
    hi: { title: 'CardioSense सहायता', ph: 'अपना सवाल लिखें', send: 'भेजें', open: 'सहायता', close: 'बंद करें',
      hi: 'नमस्ते। मैं CardioSense के बारे में हिंदी या अंग्रेज़ी में सवालों के जवाब दे सकता हूँ। मैं चिकित्सा सलाह नहीं दे सकता।',
      note: 'साइट के FAQ से स्वचालित जवाब। चिकित्सा सलाह नहीं।',
      none: 'इसका जवाब मुझे नहीं मिला। नीचे दिए सवालों में से चुनें, या /report पर समस्या दर्ज करें',
      emerg: 'अगर आपको या किसी और को सीने में दर्द, साँस लेने में तकलीफ़ या बेहोशी है, तो तुरंत अपने स्थानीय आपातकालीन नंबर (भारत में 112) पर कॉल करें या नज़दीकी अस्पताल जाएँ। आपात स्थिति में यह साइट मदद नहीं कर सकती।',
      med: 'मैं चिकित्सा सलाह नहीं दे सकता और यह नहीं बता सकता कि आपको कोई बीमारी है या नहीं। CardioSense सीखने का साधन है, मेडिकल डिवाइस नहीं। कृपया योग्य डॉक्टर से मिलें।',
      chips: [['what', 'CardioSense क्या है?'], ['device', 'क्या यह मेडिकल डिवाइस है?'], ['accuracy', 'यह कितना सटीक है?'], ['privacy', 'मेरे डेटा का क्या होता है?'], ['download', 'डाउनलोड कैसे करें?'], ['account', 'साइन अप कैसे करें?']] }
  };
  function norm(s) { return String(s || '').toLowerCase().replace(/[?!.,]/g, ' '); }
  function reply(q, lang) {
    var t = norm(q), i, j;
    for (i = 0; i < EMERGENCY.length; i++) if (t.indexOf(EMERGENCY[i]) >= 0) return { text: T[lang].emerg, warn: true };
    var best = null, bs = 0;
    KB.forEach(function (e) {
      var s = 0; e.k.forEach(function (w) { if (t.indexOf(w) >= 0) s += w.length > 3 ? 2 : 1; });
      if (s > bs) { bs = s; best = e; }
    });
    if (bs < 2) { for (j = 0; j < MEDQ.length; j++) if (t.indexOf(MEDQ[j]) >= 0) return { text: T[lang].med, warn: true }; }
    if (best && bs >= 1) return { text: best[lang] };
    return { text: T[lang].none };
  }
  window.CSChat = { reply: reply, KB: KB };
  if (typeof document === 'undefined') return;

  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }
  var lang = 'en'; try { lang = localStorage.getItem('cs-chat-lang') || ((navigator.language || '').slice(0, 2) === 'hi' ? 'hi' : 'en'); } catch (e) { /* ignore */ }
  var fab, panel, log, chips, input, title, sendBtn, ph, note, started = false;

  function add(text, who, warn) {
    var m = el('div', 'cc-m ' + who + (warn ? ' warn' : ''));
    var parts = String(text).split(/(https?:\/\/[^\s]+|\/(?:features#limits|download|signup|signin|report))/g);
    parts.forEach(function (p, i) {
      if (i % 2 === 1) { var a = el('a', '', p.replace(/[.,]$/, '')); a.href = p.replace(/[.,]$/, ''); if (/^http/.test(p)) { a.target = '_blank'; a.rel = 'noopener'; } m.appendChild(a); if (/[.,]$/.test(p)) m.appendChild(document.createTextNode(p.slice(-1))); }
      else m.appendChild(document.createTextNode(p));
    });
    log.appendChild(m); log.scrollTop = log.scrollHeight;
  }
  function ask(q) {
    q = q.trim(); if (!q) return;
    if (/[ऀ-ॿ]/.test(q) && lang !== 'hi') setLang('hi');
    add(q, 'me');
    var r = reply(q, lang);
    setTimeout(function () { add(r.text, 'bot', r.warn); }, 250);
  }
  function renderChips() {
    chips.textContent = '';
    T[lang].chips.forEach(function (c) {
      var b = el('button', '', c[1]); b.type = 'button';
      b.addEventListener('click', function () { add(c[1], 'me'); var e = KB.filter(function (x) { return x.id === c[0]; })[0]; setTimeout(function () { add(e[lang], 'bot'); }, 250); });
      chips.appendChild(b);
    });
  }
  function setLang(l) {
    lang = l; try { localStorage.setItem('cs-chat-lang', l); } catch (e) { /* ignore */ }
    if (!panel) return;
    var bs = panel.querySelectorAll('.cc-lang button'); for (var i = 0; i < bs.length; i++) bs[i].setAttribute('aria-pressed', String(bs[i].dataset.l === l));
    title.textContent = T[l].title; input.placeholder = T[l].ph; sendBtn.textContent = T[l].send; note.textContent = T[l].note; fab.querySelector('span').textContent = T[l].open;
    panel.querySelector('.cc-x').setAttribute('aria-label', T[l].close); renderChips();
  }
  function build() {
    fab = el('button', 'cc-fab'); fab.type = 'button'; fab.setAttribute('aria-expanded', 'false'); fab.setAttribute('aria-controls', 'cc-panel');
    fab.innerHTML = '<img src="/img/llama.svg" alt="" width="38" height="38"><span></span>';
    panel = el('div', 'cc-panel'); panel.id = 'cc-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Help chat');
    var head = el('div', 'cc-head'); var av = el('img', 'cc-av'); av.src = '/img/llama.svg'; av.alt = ''; av.width = 36; av.height = 36; head.appendChild(av); title = el('b'); head.appendChild(title);
    var lg = el('div', 'cc-lang'); [['en', 'EN'], ['hi', 'हिं']].forEach(function (p) { var b = el('button', '', p[1]); b.type = 'button'; b.dataset.l = p[0]; b.addEventListener('click', function () { setLang(p[0]); }); lg.appendChild(b); });
    head.appendChild(lg); var x = el('button', 'cc-x', '×'); x.type = 'button'; head.appendChild(x);
    log = el('div', 'cc-log'); log.setAttribute('aria-live', 'polite'); chips = el('div', 'cc-chips');
    var form = el('form', 'cc-form'); input = el('input'); input.type = 'text'; input.maxLength = 200; input.setAttribute('aria-label', 'Question'); sendBtn = el('button'); sendBtn.type = 'submit';
    form.append(input, sendBtn); note = el('div', 'cc-note');
    panel.append(head, log, chips, form, note); document.body.append(panel, fab);
    form.addEventListener('submit', function (e) { e.preventDefault(); var v = input.value; input.value = ''; ask(v); });
    function toggle(o) { panel.classList.toggle('open', o); fab.setAttribute('aria-expanded', String(o)); if (o) { if (!started) { started = true; add(T[lang].hi, 'bot'); } input.focus(); } }
    fab.addEventListener('click', function () { toggle(!panel.classList.contains('open')); });
    x.addEventListener('click', function () { toggle(false); fab.focus(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && panel.classList.contains('open')) toggle(false); });
    setLang(lang);
    var seen = false; try { seen = sessionStorage.getItem('cs-chat-greeted'); } catch (e) { /* ignore */ }
    if (!seen) setTimeout(function () {
      if (panel.classList.contains('open')) return;
      var tip = el('div', 'cc-tip', lang === 'hi' ? 'नमस्ते! कोई सवाल है?' : 'Namaste! Any questions?'); tip.setAttribute('role', 'status');
      document.body.appendChild(tip); try { sessionStorage.setItem('cs-chat-greeted', '1'); } catch (e) { /* ignore */ }
      setTimeout(function () { tip.remove(); }, 6000); fab.addEventListener('click', function () { tip.remove(); }, { once: true });
    }, 5000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build); else build();
})();
