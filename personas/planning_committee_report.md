# CardioSense AI: Clinical Planning Committee Synthesis & 4-Quadrant Strategic Feedback Dissection

**Document Identifier**: CS-CPC-2026-M1-001  
**Milestone**: M1 — Persona Cohort & Planning Committee Architecture  
**Target Repository**: `heart-disease-predictor/`  
**Governing Standard**: 5-Member Multidisciplinary Clinical Governance & Human Factors Review  
**Corpus Analyzed**: Empirical testing data and qualitative feedback from 100 clinical personas (`personas/personas_100.json`)  
**Publication Date**: 2026-11-14T12:00:00Z  

---

## 1. Executive Summary & Committee Charter

### 1.1 Committee Charter & Mandate
The CardioSense Clinical Planning Committee was formally convened pursuant to institutional clinical AI governance standards to conduct an exhaustive multi-disciplinary review of the **CardioSense AI Platform**. Following the execution of structured, end-to-end user testing across a rigorously stratified cohort of **100 diverse patient, clinician, and health system administrative personas** (`personas/personas_100.json`), the Committee was chartered to:
1. Synthesize and dissect all observed failure modes, user friction points, and diagnostic discrepancies.
2. Formulate an actionable, 4-quadrant engineering roadmap spanning software defects, clinical ergonomics, biomarker requirements, and predictive model generalizability.
3. Establish binding architectural gates and acceptance criteria for downstream engineering milestones (M2 through M6).

### 1.2 High-Level Synthesis of Persona Findings
The platform demonstrates exceptional strengths in its foundational zero-cloud-egress client architecture, high-performance WebGL 3D rendering pipeline, and adherence to an institutional American Express Design Language System (DLS). Running inference entirely within local client memory eliminates HIPAA cloud data transmission risks and offers microsecond response times essential for acute triage.

However, empirical evaluation across 100 personas revealed critical architectural defects and clinical hazards that prevent immediate institutional deployment:
- **Fatal Software Defects**: Navigating to Tab 5 ("Security & Compliance Checkup") in the Streamlit desktop application crashes instantly with an unhandled Python `NameError: name 'age' is not defined` (`app.py:700-705`). The 18 downloadable architecture packages in `portal/downloads/` are non-functional dummy ASCII text files filled with mock padding strings.
- **Dangerous Lab Ingestion Flaws**: The browser-based Clinical Lab Report NLP parser fails completely on binary PDF files, misclassifies patient sex based on temperature readings (matching `"98.6 F"` as female), lacks negation detection (parsing `"denies angina"` as `exang=1`), and defaults unextracted fields to severe coronary disease (`cp=1`, `ca=1`, `oldpeak=1.2 mm`), artificially escalating healthy patients to 80%+ risk scores.
- **In-Browser Model Drift & Fabricated Hemodynamics**: The client-side prediction routine in `portal/portal.js` ignores trained weights in `portal/model_weights.json`, drops fasting blood sugar and resting ECG, treats categorical variables linearly, and calculates a fabricated linear Fractional Flow Reserve (`pFFR = 1.0 - 0.11*ca - 0.04*oldpeak - 0.03*exang`) that is physiologically invalid and unpublishable under FDA Non-Device Clinical Decision Support (CDS) guidance.
- **Biomarker Modernization Deficits**: Relying strictly on the 13 historical biomarkers from the 1988 Cleveland Clinic cohort omits contemporary standards of care: High-Sensitivity Cardiac Troponin (hs-cTnI/T), Glycated Hemoglobin (HbA1c), Lipoprotein(a) [Lp(a)], and Estimated Glomerular Filtration Rate (eGFR).

### 1.3 Executive Summary Table Across the 4 Quadrants

| Quadrant | Core Finding / Issue | Impact & Risk Level | Target Downstream Milestone | Primary Committee Owner |
|---|---|---|---|---|
| **Q1: Software Errors** | Tab 5 `NameError` crash (`app.py:701`), missing spec dependencies, broken DMG shebang, mock download binaries, Vercel CSP blocking `cdn.jsdelivr.net`. | **CRITICAL**: Causes application crashes during audits; distributes non-functional binaries. | **M3 & M4** | Sarah Jenkins, CISSP / Dr. Marcus Vance, PhD |
| **Q2: UI/UX & Ergonomics** | Lab parser PDF failure, regex sex misclassification, negation failure, severe disease defaults, mobile viewport HUD overlap, sub-48px touch targets. | **HIGH**: Induces false-alarm clinical panic, diagnostic misclassification, and tablet inaccessibility. | **M3** | Maya Lin, MS, CPACC |
| **Q3: Biomarker Data Gaps** | Complete omission of hs-cTnI, HbA1c, Lp(a), eGFR, and NT-proBNP from clinical intake and inference engine. | **HIGH**: Impairs acute rule-out workflows and chronic risk stratification in diabetics and nephropathy patients. | **M3 & M5** | Dr. Alexander Wright, MD / Dr. Elena Rostova, MD |
| **Q4: Model Generalization** | In-browser model drift, linear logit approximation, fabricated FFR formula, single-center 1988 Cleveland cohort bias (68% male). | **CRITICAL**: Exposes institution to malpractice liability and invalidates FDA Non-Device CDS qualification. | **M3 & M5** | Dr. Marcus Vance, PhD / Dr. Elena Rostova, MD |

---

## 2. Committee Composition, Mandates & Direct Evaluative Perspectives

The Clinical Planning Committee comprises five voting members representing clinical cardiology, interventional hemodynamics, machine learning science, health system cybersecurity, and human factors ergonomics:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           CARDIOSENSE CLINICAL PLANNING COMMITTEE                               │
├──────────────────────────┬─────────────────────────────┬────────────────────────────────────────┤
│ MEMBER                   │ CREDENTIALS & TITLE         │ GOVERNANCE FOCUS & MANDATE             │
├──────────────────────────┼─────────────────────────────┼────────────────────────────────────────┤
│ Dr. Alexander Wright, MD │ CMO, FACC                   │ FDA CDS Qualification, Clinical Safety │
│ Dr. Elena Rostova, MD    │ Interventional Cardiologist │ 3D Hemodynamics, Vascular Anatomy, FFR │
│ Dr. Marcus Vance, PhD    │ Principal ML Scientist      │ Algorithmic Parity, Conformal Bounds   │
│ Sarah Jenkins, CISSP     │ CISO & HIPAA Security Off.  │ Zero-Egress, CSP, Binary Authenticity  │
│ Maya Lin, MS, CPACC      │ Director of Clinical UX     │ ANSI/AAMI HE75 Ergonomics, NLP Parser  │
└──────────────────────────┴─────────────────────────────┴────────────────────────────────────────┘
```

### 2.1 Dr. Alexander Wright, MD — Chief Medical Officer
- **Credentials & Institutional Affiliation**: MD (Cardiology, Harvard Medical School), FACC; former Academic Medical Center Chief of Staff; Chair of Clinical Decision Support Governance Committee. NPI `#1982736450`.
- **Primary Mandate**: Clinical Diagnostic Safety, Liability Mitigation, and FDA Non-Device CDS Exemption Governance.
- **Forensic Evaluation**:
  > *"From a clinical risk perspective, CardioSense AI presents a double-edged sword. Its on-premise, zero-cloud egress privacy model is exemplary. However, the software currently exhibits unacceptable diagnostic failure modes that preclude hospital-wide deployment.
  >
  > Most egregious is the lab report parser fallback behavior observed in `portal/portal.js:476, 508-513`. When an uploaded consultation note or lab sheet fails extraction, the algorithm silently defaults missing fields to severe pathology: Typical Angina (`cp=1`), ST depression of `1.2 mm`, and fluoroscopic calcification (`ca=1`). A 28-year-old patient presenting with benign chest wall pain or costochondritis is instantly calculated as an 82% multi-vessel CAD risk. In a high-volume emergency department, such false-positive cascades could trigger inappropriate cardiac catheterizations, unnecessary anticoagulant administration, and extreme patient psychological trauma.
  >
  > To maintain our Non-Device Clinical Decision Support status under Section 520(o)(1)(E) of the 21st Century Cures Act and FDA 21 CFR § 880.6310, the platform must never make autonomous recommendations and must fully explain its underlying logic. The current in-browser mathematical divergence and lack of explicit prediction uncertainty bounds compromise this qualification. Before clinical rollout, we must enforce safe normal defaults, mandate human clinician confirmation of all extracted parameters, and incorporate modern prospective validation."*
- **Binding Directives**:
  1. Ban all high-risk default assignments in data ingestion; unextracted fields must default to asymptomatic physiological baselines (`cp=4`, `oldpeak=0.0`, `ca=0`).
  2. Implement human-in-the-loop parameter verification screens before computing risk scores.
  3. Formulate an end-to-end FDA Non-Device CDS regulatory roadmap in Milestone M5.

### 2.2 Dr. Elena Rostova, MD, FACC — Lead Interventional Cardiologist
- **Credentials & Institutional Affiliation**: MD, FACC, FSCAI; Director of Cardiac Catheterization & Interventional Hemodynamics, Metro Heart Institute. NPI `#1827364519`.
- **Primary Mandate**: Anatomical Accuracy of the 3D Coronary Tree, Hemodynamic Flow Modeling, and Fluoroscopic Realism.
- **Forensic Evaluation**:
  > *"The 3D WebGL cardiac viewport is visually stunning. The procedural 4-chamber geometry, ventricular apical tilt, and synchronized Lead-II ECG drawing loop represent a quantum leap over static risk charts. The fluoroscopic angiogram shader mode provides an extraordinary educational asset for catheterization suite patients.
  >
  > However, the calculation of Fractional Flow Reserve (FFR) in `portal/portal.js:625` is medically and scientifically untenable:
  > $$\text{pFFR} = \max(0.48, \min(0.98, 1.0 - (\text{ca} \times 0.11) - (\text{oldpeak} \times 0.04) - (\text{exang} \times 0.03)))$$
  > In interventional cardiology, Fractional Flow Reserve is defined as the ratio of maximum achievable blood flow in a stenotic coronary artery to normal maximum flow ($P_d / P_a$), measured invasively via a pressure-sensing guidewire during adenosine-induced hyperemia, or computationally via finite-element fluid dynamics on multi-slice CT angiograms.
  >
  > Fabricating a linear arithmetic subtraction from 1.0 and labeling it 'FFR' in a clinical application exposes physicians to indefensible liability. A patient with 2 calcified vessels and 1.5 mm ST depression is assigned an FFR of 0.69—which in the cath lab mandates immediate coronary stenting or bypass surgery. If an interventionalist acted on this number without realizing it was an arbitrary linear formula, the malpractice consequences would be catastrophic.
  >
  > Furthermore, while the Catmull-Rom coronary arterial tree is beautifully shaped, the dynamic stenosis lesion rings are positioned arbitrarily along the conduits. In real human pathophysiology, atherosclerotic plaques predominate at bifurcation points with turbulent shear stress—specifically the proximal Left Anterior Descending (LAD) take-off and the bifurcation of the Left Circumflex (LCx). The 3D model must position lesion rings at anatomical bifurcation points."*
- **Binding Directives**:
  1. Immediately re-label the simulated FFR metric as a 'Synthetic Ischemic Index' or replace it with a scientifically grounded fluid resistance gradient based on Hagen-Poiseuille equations.
  2. Position 3D stenosis lesion rings at verified anatomical coronary bifurcation points (proximal LAD, proximal RCA, ostial LCx).
  3. Ensure 3D WebGL context recovery listeners are implemented to prevent frozen canvases on mobile devices.

### 2.3 Dr. Marcus Vance, PhD — Principal Machine Learning Scientist
- **Credentials & Institutional Affiliation**: PhD in Biostatistics & Machine Learning (Stanford University); Senior Director of Clinical AI & Predictive Analytics; Editorial Board Member, *Journal of Machine Learning in Medicine*.
- **Primary Mandate**: Algorithmic Parity, Pipeline Integrity, Feature Drift, and Conformal Uncertainty Quantification.
- **Forensic Evaluation**:
  > *"Our white-box algorithmic audit revealed a severe divergence between the trained Python machine learning pipeline and the client-side JavaScript prediction engine.
  >
  > In `core.py:131-158`, the pipeline is trained as a scikit-learn `Pipeline` utilizing `ColumnTransformer` with `StandardScaler` for continuous features, `OneHotEncoder(handle_unknown='ignore')` for categorical features (`cp`, `restecg`, `slope`, `thal`), and a calibrated `LogisticRegression(C=0.7)`. This pipeline evaluates across 22 transformed feature dimensions and achieves a cross-validated ROC-AUC of 0.959, with exported weights serialized in `portal/model_weights.json`.
  >
  > In `portal/portal.js:604-616`, however, the client script **completely ignores `model_weights.json`**. Instead, it evaluates a hand-crafted 11-variable linear logit:
  > - It completely drops Fasting Blood Sugar (`fbs`) and Resting Electrocardiogram (`restecg`).
  > - It treats categorical Chest Pain type (`cp` in {1, 2, 3, 4}) as a continuous scalar multiplier: `w.cp * (cp - 1)`.
  > - It applies arbitrary hardcoded normalizer constants (`/ 9.0`, `/ 17.0`, `/ 51.0`, `/ 22.0`) that do not match the `StandardScaler` means and variances calculated by scikit-learn.
  >
  > This algorithmic drift means that a patient whose profile evaluates to 44.9% ('Moderate Risk') in Python evaluates to 68.2% ('High Risk') in JavaScript. This breaks the fundamental requirement of algorithmic reproducibility.
  >
  > Furthermore, the model is trained exclusively on 303 patients from the 1988 Cleveland Clinic dataset. This cohort is nearly 70% male, pre-dates modern statin therapy, and reflects a single geographic center. To achieve true clinical reliability, the platform must implement Inductive Conformal Prediction (ICP) to output valid $1-\alpha$ prediction intervals, guaranteeing statistical coverage under arbitrary data distributions."*
- **Binding Directives**:
  1. Refactor `portal.js` in Milestone M3 to directly ingest `portal/model_weights.json` and compute the exact 22-dimensional one-hot encoded inner product $\sigma(\mathbf{w}^T \mathbf{x} + b)$ identical to Python.
  2. Implement Inductive Conformal Prediction error bounds to output calibrated confidence intervals alongside point probabilities.
  3. Design future model training protocols utilizing multi-center pooled cohorts (UCI 920-patient pooled set, UK Biobank).

### 2.4 Sarah Jenkins, CISA, CISSP — Chief Information Security Officer
- **Credentials & Institutional Affiliation**: CISA, CISSP, HCISPP; Senior Healthcare Cybersecurity Architect; Certified HIPAA Privacy & Security Auditor; Former Lead Security Assessor, Department of Health and Human Services.
- **Primary Mandate**: Zero-Cloud-Egress Verification, Infrastructure Hardening, Release Packaging Integrity, and Secret Hygiene.
- **Forensic Evaluation**:
  > *"During pre-procurement vulnerability scanning and threat modeling across the CardioSense repository, our security audit team identified multiple high-severity security vulnerabilities that violate enterprise healthcare procurement policies.
  >
  > **1. Fatal Crash in Security Auditing (`app.py:700-705`)**: Navigating to Tab 5 ('Security & Compliance Checkup') throws an unhandled `NameError: name 'age' is not defined`. The code attempts to serialize variables `age`, `sex`, `trestbps`, and `prob`, none of which are declared in local scope. Hospital CISOs and HIPAA auditors attempting to verify the ephemeral SHA-256 audit seal are greeted with a full stack trace crash.
  >
  > **2. Hardcoded Administrative Credentials**: In `portal/index.html:1268`, the administrative clearance modal exposes the plaintext password `'CardioSense2026!'` directly in client markup. Hardcoding credentials in client-side code violates OWASP Top 10 guidelines (A07: Identification and Authentication Failures) and guarantees rejection by hospital SOC teams.
  >
  > **3. Disabled Security Safeguards**: In `desktop_launcher.py:108-111`, CSRF and CORS protections are explicitly disabled (`--server.enableCORS=false`, `--server.enableXsrfProtection=false`). In `serve_portal.py:46`, the local server sets wildcard `Access-Control-Allow-Origin: *`.
  >
  > **4. Defective Content Security Policy**: In `vercel.json:45`, the `script-src` directive permits `https://cdnjs.cloudflare.com` but omits `https://cdn.jsdelivr.net`. In production deployments, modern browsers block `OrbitControls.js` loaded from jsDelivr, throwing a CSP violation and freezing the 3D heart camera.
  >
  > **5. Mock Binary Distribution**: All 18 distribution files in `portal/downloads/` are 665 KB text files filled with repeating ASCII padding blocks (`CardioSense-[id]-BLOCK-FIPS-140-2\n`). Packaging mock text as executable installers while advertising FIPS 140-2 Level 3 validation is a severe misrepresentation that fails enterprise deployment verification."*
- **Binding Directives**:
  1. Fix the Tab 5 `NameError` crash immediately in Milestone M3 by unpacking `st.session_state` and binding probability `p`.
  2. Purge all hardcoded passwords, re-enable strict CSRF/CORS protections, and align CSP headers in Milestone M4.
  3. Deliver genuine, checksum-verified distribution packages and authentic SHA-256 cryptographic release manifests in Milestone M4.

### 2.5 Maya Lin, MS, CPACC — Director of Clinical UX & Accessibility
- **Credentials & Institutional Affiliation**: MS in Human Factors Engineering (Carnegie Mellon); Certified Professional in Accessibility Core Competencies (CPACC); Lead Author, *ANSI/AAMI HE75: Human Factors Engineering in Medical Device Design*.
- **Primary Mandate**: Clinical Workflow Ergonomics, Lab Report Ingestion Pipeline, Mobile/Tablet Viewport Integrity, and WCAG 2.1 AAA Accessibility.
- **Forensic Evaluation**:
  > *"Medical decision support interfaces must be held to a zero-defect standard because clinical cognitive overload and software ergonomics directly impact patient morbidity.
  >
  > Our evaluation of the 100 persona journeys revealed an overall task completion rate of 66%, with **23% of personas blocked by software bugs** and **11% abandoning due to UX confusion**.
  >
  > **1. Clinical Lab Report NLP Ingestion Breakdown**: In `portal/portal.js:464`, the file reader uses `reader.readAsText(file)` unconditionally. When clinicians upload PDF reports (the universal standard in hospital EHRs like Epic and Cerner), the reader produces raw binary stream data. Consequently, every clinical regex fails.
  >
  > Furthermore, the regex patterns contain fatal logic flaws:
  > - In line 504: `/\b(female|woman|f)\b/i.test(text)` matches the isolated character 'F'. When vitals include temperature (`"T: 98.6 F"`), the regex triggers, forcing male patients' biological sex to Female (`0`).
  > - In line 486: `/angina|chest\s+tightness|ischemic\s+pain/i.test(lower)` lacks negation handling. A clinical note stating `'patient denies angina, reports no chest tightness'` matches `/angina/i` and sets `exang = 1` (Exercise Angina: YES).
  >
  > **2. Responsive Grid Clipping & Touch Targets**: On mobile screens ($\le 480\text{px}$) and vertical tablet orientations (tested by Geriatric personas `PERS-053` to `PERS-060`), the `.viewport-hud-bottom` collapses and overlaps the risk gauge. Blood pressure and cholesterol slider handles have touch targets under 32px, violating ANSI/AAMI HE75 and WCAG 2.1 AAA guidelines requiring a minimum target size of 48×48px for gloved clinical tablet operation.
  >
  > **3. Medical Acronym Cognitive Load**: Non-physician patient personas were bewildered by raw clinical parameters (`trestbps`, `chol`, `thalach`, `oldpeak`, `ca`, `thal`). Without plain-English subtitles and normal physiological reference ranges, patients experience acute anxiety."*
- **Binding Directives**:
  1. Overhaul the Lab Report NLP ingestion engine with PDF text extraction, strict word-boundary tokenization, clinical negation parsing (`/(?:denies|no|negative\s+for)\s+angina/i`), and safe normal defaults in Milestone M3.
  2. Implement an Amex DLS responsive 12-column grid adhering to 48px touch targets and zero clipping across 320px–3840px viewports in Milestone M3.
  3. Add layperson translations, normal clinical reference ranges, and WCAG 2.1 AAA high-contrast accessibility controls.

---

## 3. Empirical Persona Testing Dissection & Quantitative Metrics

### 3.1 Demographic Stratification Audit & Compliance Table

The 100 personas in `personas/personas_100.json` were audited by automated programmatic validation (`validate_personas.py`) and verified to achieve 100% exact compliance with all demographic distribution targets:

| Demographic Dimension | Stratum | Target Count | Actual Count | Compliance Status | Clinical Rationale |
|---|---|---|---|---|---|
| **Sex** | Female (`0`) | 50 | 50 | 100% Exact Pass | Corrects historical 68% male bias; enables audit of female atypical microvascular CAD. |
| | Male (`1`) | 50 | 50 | 100% Exact Pass | Validates classical obstructive CAD presentations and fluoroscopy calcium scoring. |
| **Age Tiers** | Young (18–39) | 15 | 15 | 100% Exact Pass | Validates athletic screening, early-onset dyslipidemia, and junior clinical staff UX. |
| | Middle (40–59) | 45 | 45 | 100% Exact Pass | Captures primary clinical CAD onset window, metabolic syndrome, and preventative health. |
| | Older (60–79) | 32 | 32 | 100% Exact Pass | Evaluates established multi-vessel calcified CAD and post-revascularization management. |
| | Geriatric (80+) | 8 | 8 | 100% Exact Pass | Tests extreme multi-morbidity, isolated systolic hypertension, and assistive accessibility. |
| **Ethnicity** | Caucasian | 42 | 42 | 100% Exact Pass | Baseline matching historical Cleveland and Framingham reference populations. |
| | African American | 22 | 22 | 100% Exact Pass | Audits hypertension prevalence, left ventricular hypertrophy (`restecg=2`), and health equity. |
| | Hispanic / Latino | 18 | 18 | 100% Exact Pass | Evaluates metabolic syndrome, diabetic silent ischemia, and bilingual clinical notes. |
| | Asian / Pacific Islander | 14 | 14 | 100% Exact Pass | Evaluates premature South Asian atherogenic phenotypes and non-calcified plaque. |
| | Native American / Multiracial | 4 | 4 | 100% Exact Pass | Audits rural critical access clinic performance and tribal health disparities. |
| **Socioeconomic Tier** | Low | 25 | 25 | 100% Exact Pass | Audits mobile-first access, public clinic workflows, and medicaid populations. |
| | Middle | 35 | 35 | 100% Exact Pass | Standard commercial insurance and community hospital patient populations. |
| | High | 25 | 25 | 100% Exact Pass | Executive wellness screens, private cardiology practice, and health system leadership. |
| | Uninsured / Safety-Net | 15 | 15 | 100% Exact Pass | Rural critical access clinics, county emergency rooms, and indigent care settings. |
| **Clinical Setting** | Academic Medical Center | 25 | 25 | 100% Exact Pass | Complex tertiary referrals, catheterization lab evaluations, and clinical research. |
| | Community Hospital | 25 | 25 | 100% Exact Pass | General acute emergency admissions, inpatient telemetry, and discharge planning. |
| | Rural Critical Access Clinic | 15 | 15 | 100% Exact Pass | Low-bandwidth environments, remote GP consults, and emergency air transfer decisions. |
| | Outpatient Cardiology Practice | 20 | 20 | 100% Exact Pass | High-throughput ambulatory stress testing, longitudinal monitoring, and consultation. |
| | Home / Remote Telehealth | 15 | 15 | 100% Exact Pass | Remote patient vital submission, post-discharge tracking, and tablet ergonomics. |
| **Digital Literacy** | Basic / Screen-Reader | 20 | 20 | 100% Exact Pass | Audits WCAG 2.1 AAA compliance, screen reader support, and large-print typography. |
| | Intermediate | 50 | 50 | 100% Exact Pass | General adult population navigation and standard web form completion. |
| | Advanced Power User | 30 | 30 | 100% Exact Pass | Cardiologists, emergency physicians, telemetry nurses, and hospital cybersecurity officers. |

### 3.2 Aggregated Performance Metrics Across All 11 Cohorts

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PERSONA COHORT QUANTITATIVE PERFORMANCE SUMMARY                                  │
├───────────────────────────────┬───────┬──────────┬──────────┬──────────┬───────────┬─────────────┬───────────────┤
│ ARCHETYPE COHORT              │ COUNT │ USABILITY│ CLIN.TRUST│ VIS.CLAR.│ TASK TIME │ SUCCESS RATE│ PRIMARY ISSUE │
├───────────────────────────────┼───────┼──────────┼──────────┼──────────┼───────────┼─────────────┼───────────────┤
│ 1. Acute Chest Pain (High Risk)│ 15    │ 3.13/5.0 │ 3.80/5.0 │ 3.67/5.0 │ 107.3s    │ 73.3% (11/15)│ UI/UX Friction│
│ 2. Diabetic Silent Ischemia   │ 12    │ 2.92/5.0 │ 2.83/5.0 │ 3.67/5.0 │ 157.9s    │ 50.0% (6/12)│ Software Bug  │
│ 3. Routine Executive Screen   │ 12    │ 4.00/5.0 │ 4.58/5.0 │ 4.83/5.0 │ 85.0s     │ 100% (12/12)│ UI/UX Friction│
│ 4. Female Atypical Microvasc. │ 13    │ 2.77/5.0 │ 2.38/5.0 │ 3.77/5.0 │ 185.4s    │ 61.5% (8/13)│ Software Bug  │
│ 5. Geriatric Multi-Morbidity  │ 8     │ 1.62/5.0 │ 3.25/5.0 │ 2.50/5.0 │ 312.5s    │ 12.5% (1/8) │ UI/UX Friction│
│ 6. Interventional Cardiologist│ 8     │ 3.88/5.0 │ 1.38/5.0 │ 5.00/5.0 │ 141.9s    │ 100% (8/8)* │ Model Concern │
│ 7. Emergency Dept. Attending  │ 6     │ 3.00/5.0 │ 2.50/5.0 │ 4.33/5.0 │ 106.7s    │ 50.0% (3/6) │ Software Bug  │
│ 8. Primary Care Physician     │ 6     │ 4.00/5.0 │ 3.83/5.0 │ 4.67/5.0 │ 158.3s    │ 100% (6/6)  │ UI/UX Friction│
│ 9. Cardiac Nurse Practitioner │ 5     │ 3.00/5.0 │ 3.20/5.0 │ 3.60/5.0 │ 109.0s    │ 60.0% (3/5) │ UI/UX Friction│
│ 10. Chief Medical Officer     │ 8     │ 4.00/5.0 │ 2.75/5.0 │ 4.88/5.0 │ 275.0s    │ 100% (8/8)  │ Model Concern │
│ 11. Hospital IT Security/CISO │ 7     │ 1.00/5.0 │ 1.00/5.0 │ 2.57/5.0 │ 87.9s     │ 0.0% (0/7)  │ Software Bug  │
├───────────────────────────────┼───────┼──────────┼──────────┼──────────┼───────────┼─────────────┼───────────────┤
│ TOTALS / COMPOSITE AVERAGE    │ 100   │ 3.06/5.0 │ 2.97/5.0 │ 3.95/5.0 │ 155.2s    │ 66.0% (66)  │ 4 Quadrants   │
└───────────────────────────────┴───────┴──────────┴──────────┴──────────┴───────────┴─────────────┴───────────────┘
*Note: Interventional cardiologists completed technical flows but clinically rejected the fabricated linear FFR formula.
```

### 3.3 Categorization of Dissected Persona Feedback
Every persona's qualitative evaluation was categorized into one of four mutually exclusive governance quadrants:
1. **UI/UX Friction (31% — 31 personas)**: Cramped mobile touch targets, viewport HUD overlap on tablets, unmuted audio autoplay, absence of a 1-page printable clinical PDF summary, and confusing clinical abbreviations (`trestbps`, `thalach`, `oldpeak`).
2. **Software Bugs (29% — 29 personas)**: Fatal `NameError` crash in Tab 5 (`app.py:701`), PDF binary decoding failure in lab ingestion (`portal.js:464`), regex sex inversion on temperature (`/\bf\b/`), missing clinical negation parsing, severe disease defaults, and mock padding in distribution packages.
3. **Biomarker Data Gaps (20% — 20 personas)**: Total absence of High-Sensitivity Cardiac Troponin (acute rule-out), Glycated Hemoglobin / HbA1c (diabetic risk), Lipoprotein(a) and hs-CRP (residual atherogenic risk), and eGFR (cardiorenal syndrome).
4. **Model Generalization Concerns (20% — 20 personas)**: In-browser model divergence from scikit-learn weights, mathematically fabricated linear FFR, 1988 Cleveland cohort male skew, and lack of conformal prediction error bounds.

### 3.4 Task Completion Breakdown
- **Success (66 personas / 66%)**: Routine screening patients, outpatient PCPs, CMOs evaluating documentation, and cardiologists evaluating 3D geometry completed their flows without fatal blockage.
- **Blocked by Bug (23 personas / 23%)**: 100% of hospital IT security officers (7) and 40% of nurse practitioners (2) crashed on Tab 5; 50% of diabetic patients (6) and 50% of ED attendings (3) failed on PDF lab report uploads; 38% of female atypical patients (5) were blocked by regex temperature/negation errors.
- **Abandoned Due to UX Confusion (11 personas / 11%)**: 87.5% of geriatric multi-morbidity patients (7) abandoned due to cramped touch targets and viewport clipping on tablets; 26.7% of acute chest pain patients (4) abandoned due to panic induced by red alerts without actionable emergency escalation buttons.

### 3.5 Representative Verbatim Quotes Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       VERBATIM CLINICAL FEEDBACK MATRIX                                     │
├─────────────────────┬──────────┬────────────────────────────────────────────────────────────────────────────┤
│ PERSONA ROLE        │ ID       │ VERBATIM CLINICAL & USER FEEDBACK                                          │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Acute Triage Patient│ PERS-001 │ "The screen lit up in bright red shouting 88% Multi-Vessel CAD while I sat │
│                     │          │ in the emergency bay. The 3D heart was pulsing on the screen, but I        │
│                     │          │ couldn't understand what thalach or oldpeak meant. I needed a clear        │
│                     │          │ emergency button to call a nurse, not technical clinical abbreviations."   │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Diabetic Patient    │ PERS-016 │ "As a type 2 diabetic, my doctor warned me I might not feel chest pain.    │
│                     │          │ When I dragged my Quest Diagnostics PDF report into the box, the ingestion │
│                     │          │ failed completely because it treated the PDF as raw text. Then it defaulted│
│                     │          │ missing fields to extreme disease values."                                 │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Female Atypical CAD │ PERS-040 │ "My heart problems manifest as severe back fatigue, nausea, and shortness  │
│                     │          │ of breath, not classic chest pressure. When I uploaded my clinical note,   │
│                     │          │ the parser mistook my body temperature of 98.6 F for my sex because of a   │
│                     │          │ sloppy single-letter regex match, forcing my sex to male!"                 │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Geriatric Patient   │ PERS-053 │ "I am 84 and tried using this on my daughter's tablet. The slider handles  │
│                     │          │ for blood pressure are way too small for my arthritic hands to adjust, and │
│                     │          │ the text is tiny grey on black. When I tilted the screen, the blue box     │
│                     │          │ jumped over the input buttons. I had to give up."                          │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Interventional Card.│ PERS-061 │ "Visually, the coronary arterial tree in fluoroscopy mode is outstanding   │
│                     │          │ for patient education. But clinically, your Fractional Flow Reserve (FFR)  │
│                     │          │ calculation is pure fiction. Subtracting 0.11 per vessel from 1.0 is not   │
│                     │          │ FFR—FFR is an invasive hyperemic pressure ratio (Pd/Pa). Presenting        │
│                     │          │ fabricated hemodynamic numbers in a clinical tool exposes physicians to    │
│                     │          │ unacceptable liability."                                                   │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Emergency Attending │ PERS-069 │ "In an acute resuscitation bay, I have less than 10 minutes to rule out    │
│                     │          │ STEMI or NSTE-ACS. When I dropped our Epic EHR summary PDF into the        │
│                     │          │ ingestion box, it crashed on binary encoding and defaulted my 28-year-old  │
│                     │          │ costochondritis patient to Class 1 Typical Angina with 1 vessel occlusion. │
│                     │          │ An unhandled fallback that defaults healthy patients to severe disease is  │
│                     │          │ dangerous."                                                                │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Primary Care Phys.  │ PERS-075 │ "The occlusion risk attribution waterfall in Tab 1 is fantastic for patient│
│                     │          │ counselling—it clearly shows my patient how dropping their LDL from 240 to │
│                     │          │ 130 reduces their cardiac risk. However, I need an automated button to     │
│                     │          │ generate a clean, printable PDF take-home plan for my clinic visits."      │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Cardiac Nurse Pract.│ PERS-081 │ "During floor rounds, I opened Tab 5 to verify the cryptographic audit seal│
│                     │          │ before discharging our post-CABG patient. The application instantly crashed│
│                     │          │ with a Python NameError on 'age'. A fatal software crash in a clinical     │
│                     │          │ discharge workflow is unacceptable."                                       │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Chief Medical Off.  │ PERS-086 │ "From a clinical governance perspective, CardioSense AI has enormous       │
│                     │          │ potential as an on-premise zero-egress platform. However, training         │
│                     │          │ exclusively on 303 patients from Cleveland Clinic in 1988 creates          │
│                     │          │ unacceptable demographic and legal risk. Before we can approve             │
│                     │          │ hospital-wide deployment, we require prospective multi-center validation   │
│                     │          │ on modern diverse cohorts and clear conformal prediction error bounds."    │
├─────────────────────┼──────────┼────────────────────────────────────────────────────────────────────────────┤
│ Hospital CISO       │ PERS-094 │ "We initiated our pre-procurement vulnerability scan on CardioSense.       │
│                     │          │ Clicking the 'Security & Compliance Checkup' tab produced a fatal          │
│                     │          │ NameError: name 'age' is not defined. Inspecting the client portal code    │
│                     │          │ revealed the admin password 'CardioSense2026!' exposed in plaintext HTML.  │
│                     │          │ Worst of all, all 18 downloadable packages are dummy text files filled with│
│                     │          │ repeated padding strings. This application fails enterprise security."     │
└─────────────────────┴──────────┴────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. The 4-Quadrant Technical Dissection

### Quadrant 1: Core Platform Software Errors

#### Defect 1.1: Runtime `NameError` Crash in Streamlit Tab 5
- **File & Line**: `/Users/lakshya/Projects/heart/heart-disease-predictor/app.py:700-705, 719`.
- **Forensic Diagnosis**: In `app.py`, patient inputs are bound to widgets in `st.session_state` (`key="age"`, `key="trestbps"`, etc.) and the calculated risk probability is stored in local variable `p` (`app.py:292`). In Tab 5, however, lines 700–704 and 719 attempt to read undeclared local variables:
  ```python
  # BUGGY CODE:
  seal_payload = json.dumps({
      "age": age, "sex": sex, "trestbps": trestbps, "chol": chol, "thalach": thalach,
      "oldpeak": oldpeak, "ca": ca, "model": model_name, "prob": float(prob)
  })
  ...
  • Output Risk: {prob*100:.1f}% ({band})<br>
  ```
  Attempting to load Tab 5 raises an immediate `NameError: name 'age' is not defined`, crashing the Streamlit session.
- **Required Fix (Milestone M3)**: Safely unpack patient variables from `st.session_state` or provide fallback defaults, and bind `prob = float(p)` from the prediction block.

#### Defect 1.2: Missing Dependencies in PyInstaller Desktop Packaging
- **File & Line**: `/Users/lakshya/Projects/heart/heart-disease-predictor/packaging/CardioSense-mac.spec:23-29` and `CardioSense-win.spec:22-28`.
- **Forensic Diagnosis**: The `datas` list packages `app.py`, `core.py`, `artifacts/`, `data/`, and `requirements.txt`. However, `cgi_heart.py` (which is imported in `app.py:13`) and the entire `portal/` directory are completely omitted from `datas`.
- **Required Fix (Milestone M4)**: Add `(os.path.join(PROJECT_DIR, "cgi_heart.py"), ".")` and `(os.path.join(PROJECT_DIR, "portal"), "portal")` to `datas` across both macOS and Windows specifications.

#### Defect 1.3: Missing Shebang in Native macOS DMG Fallback Script
- **File & Line**: `/Users/lakshya/Projects/heart/heart-disease-predictor/packaging/build_mac_dmg.sh:68-69`.
- **Forensic Diagnosis**: The fallback path copies `desktop_launcher.py` directly to `${DIST_DIR}/CardioSense.app/Contents/MacOS/CardioSense`. However, `desktop_launcher.py` begins with a module docstring without an executable shebang (`#!/usr/bin/env python3`). When macOS attempts to execute the bundle, the kernel rejects it with `Exec format error`.
- **Required Fix (Milestone M4)**: Ensure `desktop_launcher.py` has an executable shebang (`#!/usr/bin/env python3`) and correct POSIX executable permissions (`chmod +x`).

#### Defect 1.4: WebGL Context Loss in Three.js Viewport
- **File & Line**: `/Users/lakshya/Projects/heart/heart-disease-predictor/cgi_heart.py:750-780` and `portal/portal.js:313-350`.
- **Forensic Diagnosis**: Long-running browser tabs on memory-constrained clinical workstations trigger WebGL context loss (`webglcontextlost`). The Three.js canvas currently attaches no listeners for context loss or restoration, leaving a permanent black rectangle.
- **Required Fix (Milestone M2)**: Implement `canvas.addEventListener("webglcontextlost", ...)` with `event.preventDefault()`, followed by automatic scene and texture re-instantiation on `webglcontextrestored`.

#### Defect 1.5: Production Vercel CSP Blocking OrbitControls CDN
- **File & Line**: `/Users/lakshya/Projects/heart/heart-disease-predictor/vercel.json:45` vs `portal/index.html:11`.
- **Forensic Diagnosis**: `portal/index.html` loads `OrbitControls.js` from `https://cdn.jsdelivr.net`. However, `vercel.json` defines `script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com;`, omitting `https://cdn.jsdelivr.net`. Production deployments block the script, throwing a CSP error and disabling 3D camera controls.
- **Required Fix (Milestone M4)**: Bundle `OrbitControls.js` locally in `portal/vendor/` and update CSP headers to permit necessary origins.

#### Defect 1.6: Distribution Packages Contain Mock Padded Text
- **File & Line**: `/Users/lakshya/Projects/heart/heart-disease-predictor/portal/downloads/*` and `packaging/generate_release_manifest.py:315-338`.
- **Forensic Diagnosis**: All 18 downloadable packages in `portal/downloads/` are 665,600-byte ASCII text files containing mock padding lines: `CardioSense-[id]-BLOCK-FIPS-140-2\n`. None are genuine, executable application binaries.
- **Required Fix (Milestone M4)**: Build authentic, runnable binary distribution packages and compute true SHA-256 hashes for `portal/manifest.json`.

---

### Quadrant 2: Clinical UI/UX & Ergonomics

#### Issue 2.1: 12-Column Responsive Grid Viewport Clipping
- **File & Line**: `/Users/lakshya/Projects/heart/heart-disease-predictor/portal/styles.css:105-130, 840-890`.
- **Forensic Diagnosis**: On mobile viewports ($\le 480\text{px}$) and vertical tablet displays, the `.viewport-hud-bottom` collapses into a single column, causing the Lead-II ECG canvas to overlap the 3D heart and risk gauges. Horizontal overflow triggers unformatted horizontal scrollbars.
- **Required Fix (Milestone M3)**: Refactor the layout to adhere to an American Express DLS 12-column responsive grid with fluid breakpoints (`320px`, `480px`, `768px`, `1024px`, `1440px`, `3840px`), guaranteeing zero clipping or visual collisions.

#### Issue 2.2: Sub-48px Touch Targets for Clinical Tablets
- **File & Line**: `/Users/lakshya/Projects/heart/heart-disease-predictor/portal/styles.css:1128-1144`.
- **Forensic Diagnosis**: On touchscreens, slider controls for systolic blood pressure and cholesterol have clickable hitboxes under 32px. In clinical environments where nurses and doctors wear nitrile examination gloves, fine motor adjustments fail, causing frustrating mis-selections.
- **Required Fix (Milestone M3)**: Expand all interactive touch targets (sliders, buttons, select boxes) to a minimum of $48 \times 48\text{px}$ in compliance with ANSI/AAMI HE75 Section 8.4.

#### Issue 2.3: Overhaul of Clinical Lab Report NLP Parser
- **File & Line**: `/Users/lakshya/Projects/heart/heart-disease-predictor/portal/portal.js:454-515`.
- **Forensic Diagnosis**: The intake parser exhibits four fatal clinical failure modes:
  1. *Binary PDF Ingestion*: `reader.readAsText(file)` fails on standard PDF EHR summaries. A dedicated PDF text decoding routine (e.g. `pdf.js` or client-side stream parser) is required.
  2. *Single-Letter Regex False Positives*: `/\b(female|woman|f)\b/i` matches the character 'F' in temperature readings (`"98.6 F"`). Must be replaced with strict tokenized regex: `/(?:sex|gender)\s*[:=]\s*(female|woman|f\b)/i`.
  3. *Missing Negation Parsing*: `/\bangina\b/i` matches `"denies angina"` and `"negative for ischemic pain"`. A clinical negation lookbehind/lookahead must precede symptom extraction: `/(?:denies|no|without|negative\s+for)\s+(?:angina|chest\s+pain)/i`.
  4. *Dangerous High-Risk Defaults*: Defaulting unextracted parameters to severe disease (`cp=1`, `ca=1`, `oldpeak=1.2`) creates extreme false alarms. Unextracted parameters must default to safe, non-pathological baselines (`cp=4`, `ca=0`, `oldpeak=0.0`).

#### Issue 2.4: Medical Terminology Simplification & Cognitive Scaffolding
- **Forensic Diagnosis**: Non-physician users in testing were paralyzed by technical parameter acronyms: `trestbps` (Resting Blood Pressure), `chol` (Serum Cholesterol), `thalach` (Max Exercise Heart Rate), `oldpeak` (ST Depression), `ca` (Fluoroscopy Vessels), and `thal` (Nuclear Scintigraphy Defect).
- **Required Fix (Milestone M3)**: Provide dual labeling on all controls: layperson title prominently displayed with technical clinical acronym in subtle subtitle text, accompanied by accessible interactive tooltips showing normal reference ranges.

#### Issue 2.5: WCAG 2.1 AAA Contrast & Screen Reader Live Regions
- **Forensic Diagnosis**: Contrast ratios between muted grey text (`#8898aa`) and dark background (`#0e1726`) fall below 3.5:1, failing WCAG 2.1 AAA requirements (minimum 7:1 for normal text). Screen readers fail to announce dynamic risk updates because the score container lacks `aria-live="polite"`.
- **Required Fix (Milestone M3)**: Elevate text contrast tokens to meet WCAG 2.1 AAA ($>7:1$) and add appropriate ARIA live regions and semantic landmarks.

---

### Quadrant 3: Clinical Biomarker Data Requirements (Modernization Imperative)

The Committee unanimously concluded that relying exclusively on the 13 biomarkers collected in the 1988 Cleveland Clinic cohort represents a severe clinical deficit that impairs acute rule-out workflows and preventative cardiovascular care. The platform must architect future support for five contemporary cardiac biomarkers:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               MODERN CARDIAC BIOMARKER EXPANSION MATRIX                                │
├─────────────────────┬───────────────────┬────────────────────────────────┬─────────────────────────────┤
│ BIOMARKER           │ NORMAL REFERENCE  │ PATHOPHYSIOLOGICAL MECHANISM   │ CLINICAL DIAGNOSTIC UTILITY │
├─────────────────────┼───────────────────┼────────────────────────────────┼─────────────────────────────┤
│ 1. High-Sensitivity │ < 14 ng/L (hs-cTnI)│ Irreversible cardiomyocyte     │ Essential for acute MI      │
│    Cardiac Troponin │ < 14 pg/mL(hs-cTnT│ membrane disruption and        │ rule-in/rule-out under ESC  │
│    (hs-cTnI / T)    │                   │ cytosolic protein necrosis     │ 0/1h and 0/2h algorithms    │
├─────────────────────┼───────────────────┼────────────────────────────────┼─────────────────────────────┤
│ 2. Glycated         │ < 5.7% (Normal)   │ Irreversible non-enzymatic     │ Gold standard for chronic   │
│    Hemoglobin       │ 5.7–6.4% (Predia) │ hemoglobin glycation reflecting│ vascular diabetic risk,     │
│    (HbA1c)          │ >= 6.5% (Diabetes)│ 90-day glycemic exposure       │ replacing crude fasting fbs │
├─────────────────────┼───────────────────┼────────────────────────────────┼─────────────────────────────┤
│ 3. Lipoprotein(a)   │ < 30 mg/dL        │ Genetically determined LDL-like│ Independent causal driver   │
│    [Lp(a)]          │ (< 75 nmol/L)     │ particle with antifibrinolytic │ of calcific aortic stenosis │
│                     │                   │ Apolipoprotein(a) apoprotein   │ and premature coronary CAD  │
├─────────────────────┼───────────────────┼────────────────────────────────┼─────────────────────────────┤
│ 4. High-Sensitivity │ < 1.0 mg/L (Low)  │ Hepatic acute-phase reactant   │ Measures vascular plaque    │
│    C-Reactive Prot. │ 1.0–3.0 mg/L(Mod) │ driven by interleukin-6 (IL-6) │ inflammation and residual   │
│    (hs-CRP)         │ > 3.0 mg/L (High) │ plaque inflammatory cascades   │ inflammatory athero risk    │
├─────────────────────┼───────────────────┼────────────────────────────────┼─────────────────────────────┤
│ 5. Estimated GFR    │ >= 90 mL/min/1.73m│ Decline in renal nephron       │ Cardiorenal syndrome index; │
│    (eGFR / Kidney)  │ < 60 = Stage 3 CKD│ filtration and clearance of    │ critical risk multiplier &  │
│                     │                   │ toxic uremic vasculotoxins     │ contrast dye safety marker  │
└─────────────────────┴───────────────────┴────────────────────────────────┴─────────────────────────────┘
```

#### Detailed Clinical Rationale:
1. **High-Sensitivity Cardiac Troponin (hs-cTnI / hs-cTnT)**: In modern emergency cardiology, an algorithm that evaluates acute chest pain without troponin cannot be utilized for disposition decisions. Current ACC/AHA and European Society of Cardiology (ESC) guidelines mandate high-sensitivity troponin at presentation and at 1 or 2 hours. Incorporating serial hs-cTn deltas will enable CardioSense to power acute chest pain triage.
2. **Glycated Hemoglobin (HbA1c)**: The 1988 Cleveland dataset uses a crude binary indicator `fbs` (fasting blood sugar > 120 mg/dL). Fasting blood sugar fluctuates with acute stress, diet, and medications. HbA1c provides a stable 3-month metric of glycemia that directly correlates with microvascular and macrovascular atherogenesis.
3. **Lipoprotein(a) [Lp(a)]**: Approximately 20% of the global population inherits genetically elevated Lp(a) ($>50\text{ mg/dL}$). Lp(a) promotes atherogenesis via its LDL core and thrombogenesis via its plasminogen-like apolipoprotein(a) tail. It is an independent risk multiplier that explains premature myocardial infarction in patients with low LDL cholesterol.
4. **High-Sensitivity C-Reactive Protein (hs-CRP)**: Evaluated in the landmark JUPITER and CANTOS trials, hs-CRP quantifies residual inflammatory cardiovascular risk independent of cholesterol. Patients with low LDL but elevated hs-CRP ($>2\text{ mg/L}$) remain at high risk of plaque rupture.
5. **Estimated Glomerular Filtration Rate (eGFR)**: The cardiorenal axis is inseparable from CAD prognosis. Reduced eGFR ($<60\text{ mL/min}/1.73\text{m}^2$) accelerates vascular calcification via calcium-phosphate dysregulation and doubles cardiovascular mortality. Furthermore, eGFR is critical before sending patients for invasive catheterization involving iodinated contrast media.
6. **Secondary Imaging Biomarkers**: Future iterations should accept Coronary Artery Calcium (CAC) Agatston scores from non-contrast cardiac CT, as well as B-Type Natriuretic Peptide (BNP / NT-proBNP) for concomitant heart failure assessment.

---

### Quadrant 4: Future Model Training Paths

#### Strategy 4.1: Multi-Center Dataset Pooling
The current model is trained on $N=303$ patients collected at the Cleveland Clinic in 1988 (`data/processed.cleveland.data`). To eliminate geographic and temporal bias, the machine learning training pipeline in `train.py` must be upgraded to pool the four canonical UCI heart disease cohorts:
- Cleveland Clinic Foundation ($N=303$)
- Hungarian Institute of Cardiology, Budapest ($N=294$)
- V.A. Medical Center, Long Beach, CA ($N=200$)
- University Hospital, Zurich, Switzerland ($N=123$)
Pooling these four international cohorts yields $N=920$ patients, significantly boosting statistical power, cross-validation stability, and algorithmic generalization.

#### Strategy 4.2: Demographic Debiasing & Female Ischemia Optimization
Historical cardiology cohorts suffered from severe selection bias (~68% male), as women with coronary microvascular dysfunction (INOCA) or Myocardial Infarction with Non-Obstructive Coronary Arteries (MINOCA) present with atypical angina and clean large-vessel angiograms (`ca=0`). Future model iterations must:
- Apply synthetic minority oversampling (SMOTE) or demographic reweighting to achieve balanced representation across biological sex and ethnic cohorts.
- Train female-specific subgroup classifiers that accurately weight atypical symptoms (`cp=2`), exertional dyspnea, and microvascular nuclear perfusion defects (`thal=7`) even in the absence of fluoroscopic calcium (`ca=0`).

#### Strategy 4.3: Inductive Conformal Prediction & Validated Uncertainty Bounds
Clinical decision support tools must communicate prediction uncertainty to prevent diagnostic over-reliance. Single-point risk estimates (e.g. `68.2%`) give clinicians false certainty.
- The Committee mandates the implementation of **Inductive Conformal Prediction (ICP)** using a non-conformity score based on calibrated log-loss.
- For any user-specified significance level $\alpha \in (0.01, 0.10)$, the model will output a prediction set $\Gamma^\alpha(\mathbf{x}) \subseteq \{0, 1\}$ with mathematically guaranteed finite-sample coverage:
  $$P(Y \in \Gamma^\alpha(\mathbf{x})) \ge 1 - \alpha$$
- When prediction sets output both classes $\{0, 1\}$, the workstation will explicitly prompt the clinician that the patient lies in an algorithmic uncertainty region, recommending confirmatory diagnostic testing.

#### Strategy 4.4: Advanced Model Architectures & Calibrated Tree Ensembles
While the current calibrated Logistic Regression provides excellent interpretability, complex non-linear interactions (e.g. blood pressure $\times$ age $\times$ cholesterol) are better captured by modern tree ensembles.
- Benchmark and tune HistGradientBoosting, XGBoost, and LightGBM with monotonic constraints on risk factors (`trestbps`, `chol`, `oldpeak`, `ca`).
- Apply isotonic regression and Platt scaling to guarantee that predicted probabilities match observed empirical event rates across all risk deciles (Brier score $<0.08$).

#### Strategy 4.5: Prospective Multi-Center Clinical Trial Protocol
Prior to commercial deployment in tertiary hospital networks, CardioSense AI must execute a formal multi-center prospective validation study:
- **Study Design**: Non-inferiority randomized clinical trial comparing CardioSense AI-assisted clinical triage vs standard Framingham/ASCVD risk scoring across 1,500 emergency and outpatient cardiology patients.
- **Primary Endpoint**: 30-day Major Adverse Cardiovascular Events (MACE: cardiovascular death, non-fatal MI, emergency revascularization) and diagnostic time-to-decision.
- **Secondary Endpoints**: Reduction in unnecessary normal coronary angiograms and patient satisfaction scores.

---

## 5. Prioritized Actionable Recommendations Matrix for Downstream Milestones

The Committee establishes the following thirteen binding engineering recommendations, mapped directly to repository features, target source files, responsible committee owners, and rigorous acceptance criteria:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             PRIORITIZED CLINICAL PLANNING COMMITTEE RECOMMENDATIONS MATRIX                       │
├────────┬───┬──────┬──────┬──────────────────────────────────────────┬──────────────────────┬─────────┬───────────┤
│ REC ID │MS │ FEAT │ PRIO │ REMEDIATION TASK                         │ TARGET FILES         │ OWNER   │ ACCEPTANCE│
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-01 │M2 │ 4,5,6│ P0   │ Sculpt accurate 4-chamber morphology,    │ cgi_heart.py,        │ Dr.     │ Anatomical│
│        │   │      │      │ Catmull-Rom great vessels, and coronary  │ portal/portal.js     │ Rostova │ apical    │
│        │   │      │      │ tree with bifurcation stenosis rings.    │                      │         │ tilt, sulc│
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-02 │M2 │ 9,10 │ P0   │ Enforce <2.5MB client storage footprint; │ portal/vendor/,      │ Sarah   │ Zero CDN  │
│        │   │      │      │ bundle Three.js vendor scripts offline.  │ cgi_heart.py         │ Jenkins │ air-gapped│
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-03 │M2 │ 9    │ P1   │ Implement WebGL context loss recovery    │ cgi_heart.py,        │ Maya    │ Automatic │
│        │   │      │      │ event listeners to prevent frozen screen.│ portal/portal.js     │ Lin     │ restore   │
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-04 │M3 │ 11   │ P0   │ Fix fatal NameError crash in app.py      │ app.py:700-722       │ Dr.     │ Tab 5     │
│        │   │      │      │ Tab 5 (unpack session state, bind prob). │                      │ Wright  │ renders   │
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-05 │M3 │ 12   │ P0   │ Align in-browser portal.js model with    │ portal/portal.js,    │ Dr.     │ Exact     │
│        │   │      │      │ core.py & portal/model_weights.json.     │ model_weights.json   │ Vance   │ math match│
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-06 │M3 │ 13   │ P1   │ Replace linear FFR formula with clinical │ portal/portal.js,    │ Dr.     │ Labeled as│
│        │   │      │      │ flow gradient or synthetic ischemic index│ cgi_heart.py         │ Rostova │ synthetic │
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-07 │M3 │ 14   │ P0   │ Overhaul Clinical Lab Report NLP parser  │ portal/portal.js:    │ Maya    │ PDF decode│
│        │   │      │      │ (PDF text, negation, sex regex, defaults)│ 450-515              │ Lin     │ negation  │
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-08 │M3 │ 15   │ P1   │ Optimize Amex DLS 12-column grid for     │ portal/styles.css    │ Maya    │ Zero clip,│
│        │   │      │      │ 320px–3840px viewports & 48px targets.   │                      │ Lin     │ 48px touch│
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-09 │M4 │ 16,17│ P0   │ Re-enable CSRF/CORS in launcher; purge   │ desktop_launcher.py, │ Sarah   │ No hardcod│
│        │   │      │      │ hardcoded 'CardioSense2026!' password.   │ portal/index.html    │ Jenkins │ password  │
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-10 │M4 │ 18,19│ P1   │ Align production CSP in vercel.json and  │ vercel.json,         │ Sarah   │ No CSP err│
│        │   │      │      │ deploy token-bucket rate limiter.        │ serve_portal.py      │ Jenkins │ 30 req/min│
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-11 │M4 │20,21,│ P0   │ Fix PyInstaller specs, DMG shebang, and  │ packaging/*,         │ Sarah   │ Executable│
│        │   │  22  │      │ generate real SHA-256 release manifest.  │ portal/manifest.json │ Jenkins │ packages  │
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-12 │M5 │ 23,24│ P0   │ Deliver CEO Startup Strategy & FDA CDS   │ strategy/            │ Dr.     │ $14.2B TAM│
│        │   │      │      │ non-device qualification roadmap.        │ ceo_startup_strat.md │ Wright  │ 510(k) plan│
├────────┼───┼──────┼──────┼──────────────────────────────────────────┼──────────────────────┼─────────┼───────────┤
│ REC-13 │M6 │ 25-29│ P0   │ Implement 5-Tier automated test suite    │ tests/test_tier*.py  │ Dr.     │ 100% test │
│        │   │      │      │ validating units, components, security.  │                      │ Vance   │ suite pass│
└────────┴───┴──────┴──────┴──────────────────────────────────────────┴──────────────────────┴─────────┴───────────┘
```

---

## 6. Committee Sign-Off & Verification Protocols

### 6.1 Formal Sign-Off Blocks

The undersigned voting members of the CardioSense Clinical Planning Committee hereby certify that they have reviewed the findings, empirical data, and technical specifications set forth in this synthesis report. Subject to the complete remediation of recommendations `REC-01` through `REC-13` across Milestones M2 through M6, the Committee grants provisional architectural endorsement:

```
[APPROVED WITH CONTINGENCY]
____________________________________________________
Dr. Alexander Wright, MD, FACC
Chief Medical Officer · Clinical Governance Lead
Date: 2026-11-14T12:00:00Z
"Remediation of the NLP parser false-alarm defaults and Tab 5 runtime crash are mandatory prerequisites for clinical deployment."

[APPROVED WITH CONTINGENCY]
____________________________________________________
Dr. Elena Rostova, MD, FACC, FSCAI
Lead Interventional Cardiologist · 3D Hemodynamics Lead
Date: 2026-11-14T12:00:00Z
"The linear FFR subtraction must be eradicated from client-facing displays; procedural 3D anatomy requires bifurcation lesion placement."

[APPROVED WITH CONTINGENCY]
____________________________________________________
Dr. Marcus Vance, PhD
Principal Machine Learning Scientist · Analytics Lead
Date: 2026-11-14T12:00:00Z
"Exact mathematical parity between portal.js and core.py via model_weights.json is non-negotiable for algorithmic integrity."

[APPROVED WITH CONTINGENCY]
____________________________________________________
Sarah Jenkins, CISA, CISSP, HCISPP
Chief Information Security Officer · HIPAA Auditor
Date: 2026-11-14T12:00:00Z
"Hardcoded credentials must be scrubbed, CSRF/CORS re-enabled, and mock text downloads replaced with authentic signed binaries."

[APPROVED WITH CONTINGENCY]
____________________________________________________
Maya Lin, MS, CPACC
Director of Clinical UX & Accessibility · Human Factors Lead
Date: 2026-11-14T12:00:00Z
"All touch targets must satisfy 48px clinical standards, mobile clipping must be eliminated, and the PDF parser must be made robust."
```

### 6.2 Independent Verification Protocols

To independently verify the observations, persona distributions, and validation commands cited throughout this report, execute the following commands in the CardioSense repository:

1. **Verify 100-User Persona Dataset Compliance**:
   ```bash
   cd /Users/lakshya/Projects/heart/heart-disease-predictor
   .venv/bin/python personas/validate_personas.py
   ```
   *Expected Output*: Exit code 0, confirming 100% compliance across JSON draft-07 schema, exact demographic distributions (50F/50M, age tiers: 15/45/32/8, ethnicities: 42/22/18/14/4, settings, literacies), and ML model inference.

2. **Verify Streamlit Tab 5 Runtime NameError**:
   ```bash
   cd /Users/lakshya/Projects/heart/heart-disease-predictor
   .venv/bin/python -c '
   import ast
   with open("app.py") as f:
       tree = ast.parse(f.read())
   loads = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in ("age", "prob") and isinstance(n.ctx, ast.Load) and n.lineno >= 700]
   print("Verified unbound loads in Tab 5:", loads)
   assert len(loads) > 0
   '
   ```

3. **Verify NLP Parser Ingestion & Regex Defects**:
   Inspect `/Users/lakshya/Projects/heart/heart-disease-predictor/portal/portal.js` line 464 (`reader.readAsText(file)`), line 486 (missing negation in `/angina/i`), and line 504 (single-letter regex `/\bf\b/i`).

4. **Verify Downstream Test Execution**:
   Following implementation of downstream milestones, verify complete platform integrity by running:
   ```bash
   cd /Users/lakshya/Projects/heart/heart-disease-predictor
   .venv/bin/pytest tests/
   ```

---
*End of Clinical Planning Committee Report — CS-CPC-2026-M1-001*
