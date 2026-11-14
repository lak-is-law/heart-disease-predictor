"""tests/test_lab_report_parser.py
Automated Unit Test Suite for ClinicalLabReportParser (M3 Milestone).
Tests all 13 biomarkers, negation handling, PDF extraction, false-positive protection,
and safety failure modes.
"""

import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from components.lab_report_parser import ClinicalLabReportParser, is_clinically_negated


class TestClinicalLabReportParser(unittest.TestCase):
    def setUp(self):
        self.parser = ClinicalLabReportParser()

    def test_full_acs_stemi_extraction(self):
        note = """
        CLINICAL DISCHARGE SUMMARY
        Patient Age: 62
        Sex: Male
        Chief Complaint: Acute crushing substernal chest pressure (typical angina).
        Vitals: BP 168/104 mmHg, Max HR achieved: 128 bpm.
        Labs: Serum Cholesterol: 288 mg/dL, Fasting blood sugar: 140 mg/dL.
        Resting 12-lead ECG: restecg: 1 (ST-T abnormality).
        Treadmill Stress Test: Positive for exercise-induced angina.
        Peak Exercise ST depression: 3.2 mm downsloping.
        Coronary Angiogram: 3 major vessels calcified with critical LAD stenosis.
        SPECT MPI: Reversible perfusion defect in anterior myocardium.
        """
        res = self.parser.parse_text(note)
        self.assertEqual(res.extracted_count, 13)
        self.assertEqual(res.biomarkers["age"], 62)
        self.assertEqual(res.biomarkers["sex"], 1)
        self.assertEqual(res.biomarkers["cp"], 1)
        self.assertEqual(res.biomarkers["trestbps"], 168)
        self.assertEqual(res.biomarkers["chol"], 288)
        self.assertEqual(res.biomarkers["fbs"], 1)
        self.assertEqual(res.biomarkers["restecg"], 1)
        self.assertEqual(res.biomarkers["thalach"], 128)
        self.assertEqual(res.biomarkers["exang"], 1)
        self.assertAlmostEqual(res.biomarkers["oldpeak"], 3.2, places=1)
        self.assertEqual(res.biomarkers["slope"], 3)
        self.assertEqual(res.biomarkers["ca"], 3)
        self.assertEqual(res.biomarkers["thal"], 7)
        self.assertTrue(res.safe_to_predict)

    def test_clinical_negations_denies_chest_pain(self):
        note = """
        OUTPATIENT CONSULTATION
        Patient is a 55 yo male.
        Temp 98.6 F. BP 120/80 mmHg. Total cholesterol: 180 mg/dL. Fasting glucose: 95 mg/dL.
        Patient explicitly denies chest pain, denies angina, and reports no dyspnea.
        Stress ECG negative for ischemia and without ST depression.
        Resting ECG: Normal sinus rhythm.
        Catheterization: Normal coronary arteries, 0 vessels occluded.
        SPECT MPI: No perfusion defect.
        """
        res = self.parser.parse_text(note)
        self.assertEqual(res.biomarkers["sex"], 1, "Temperature 98.6 F must NOT flip sex to female!")
        self.assertEqual(res.biomarkers["cp"], 4, "Denies chest pain must evaluate to Asymptomatic (Class 4)")
        self.assertEqual(res.biomarkers["exang"], 0, "Denies angina must evaluate to exang = 0")
        self.assertAlmostEqual(res.biomarkers["oldpeak"], 0.0, places=1, msg="Without ST depression must evaluate to 0.0 mm")
        self.assertEqual(res.biomarkers["ca"], 0, "0 vessels occluded must evaluate to ca = 0")
        self.assertEqual(res.biomarkers["thal"], 3, "No perfusion defect must evaluate to thal = 3 (Normal)")

    def test_temperature_fahrenheit_false_positive_protection(self):
        note = "Vitals: Temp 98.6 F, Pulse 72 bpm, BP 120/80. Patient is a 48 yo male."
        res = self.parser.parse_text(note)
        self.assertEqual(res.biomarkers["sex"], 1)

    def test_page_number_exclusion_from_age(self):
        note = "Page 12 of 20. Confidential EHR record. Patient age: 45. Sex: female."
        res = self.parser.parse_text(note)
        self.assertEqual(res.biomarkers["age"], 45)
        self.assertEqual(res.biomarkers["sex"], 0)

    def test_fixed_dose_exclusion_from_thal(self):
        note = "Patient is on a fixed dose of atorvastatin with a fixed follow-up appointment."
        res = self.parser.parse_text(note)
        self.assertEqual(res.biomarkers["thal"], 3, "Fixed dose must NOT trigger thal = 6!")

    def test_flat_affect_exclusion_from_slope(self):
        note = "Neurological examination reveals flat affect and soft, non-tender flat abdomen."
        res = self.parser.parse_text(note)
        self.assertEqual(res.biomarkers["slope"], 1, "Flat affect must NOT trigger slope = 2!")

    def test_dna_basepair_exclusion_from_blood_pressure(self):
        note = "Genomic assay PCR produced 500 bp band. Resting blood pressure: 130/84 mmHg."
        res = self.parser.parse_text(note)
        self.assertEqual(res.biomarkers["trestbps"], 130)

    def test_hdl_cholesterol_exclusion(self):
        note = "Lipid panel: HDL chol: 45 mg/dL, LDL chol: 110 mg/dL, Total cholesterol: 215 mg/dL."
        res = self.parser.parse_text(note)
        self.assertEqual(res.biomarkers["chol"], 215)

    def test_resting_vs_max_heart_rate(self):
        note = "Resting heart rate: 68 bpm. Max exercise heart rate achieved: 168 bpm."
        res = self.parser.parse_text(note)
        self.assertEqual(res.biomarkers["thalach"], 168)

    def test_empty_document_safe_baseline_and_rejection(self):
        res = self.parser.parse_text("Grocery receipt: apples, bananas, milk.")
        self.assertEqual(res.extracted_count, 0)
        self.assertEqual(res.confidence_score, 0.0)
        self.assertFalse(res.safe_to_predict)
        self.assertEqual(res.biomarkers["cp"], 4)
        self.assertEqual(res.biomarkers["oldpeak"], 0.0)
        self.assertEqual(res.biomarkers["ca"], 0)
        self.assertEqual(res.biomarkers["trestbps"], 120)
        self.assertEqual(res.biomarkers["chol"], 195)

    def test_pure_python_pdf_stream_decompression(self):
        import zlib
        stream_content = b'BT /F1 12 Tf (Patient Age: 58. Total cholesterol: 220 mg/dL.) Tj ET'
        compressed = zlib.compress(stream_content)
        pdf_bytes = b'''%PDF-1.4
1 0 obj
<< /Length ''' + str(len(compressed)).encode() + b''' /Filter /FlateDecode >>
stream
''' + compressed + b'''
endstream
endobj
xref
0 2
0000000000 65535 f 
0000000009 00000 n 
trailer
<< /Size 2 /Root 1 0 R >>
%%EOF'''
        res = self.parser.parse_file(pdf_bytes, "test.pdf")
        self.assertEqual(res.biomarkers["age"], 58)
        self.assertEqual(res.biomarkers["chol"], 220)


if __name__ == "__main__":
    unittest.main()
