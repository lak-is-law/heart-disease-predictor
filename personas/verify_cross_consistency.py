"""Independent Cross-Consistency Verification Script between personas_100.json and planning_committee_report.md.

Authored by: teamwork_challenger (m1_challenger_2)
Objective: Assert exact statistical alignment, score distributions, quotes, and detect fabricated metrics.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from collections import Counter, defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent

ARCHETYPE_MAP = {
    "1. Acute Chest Pain (High Risk)": "Patient: Acute Chest Pain (High Risk)",
    "2. Diabetic Silent Ischemia": "Patient: Diabetic Silent Ischemia",
    "3. Routine Executive Screen": "Patient: Routine Executive Screen (Low Risk)",
    "4. Female Atypical Microvasc.": "Patient: Female Atypical Microvascular Angina",
    "5. Geriatric Multi-Morbidity": "Patient: Geriatric Multi-Morbidity",
    "6. Interventional Cardiologist": "Clinician: Interventional Cardiologist",
    "7. Emergency Dept. Attending": "Clinician: Emergency Department Attending",
    "8. Primary Care Physician": "Clinician: Primary Care Physician (PCP)",
    "9. Cardiac Nurse Practitioner": "Clinician: Cardiac Care Nurse Practitioner",
    "10. Chief Medical Officer": "Administrator: Chief Medical Officer (CMO)",
    "11. Hospital IT Security/CISO": "Administrator: Hospital IT Security & HIPAA Officer",
}

def run_cross_verification() -> dict:
    json_path = REPO_ROOT / "personas" / "personas_100.json"
    report_path = REPO_ROOT / "personas" / "planning_committee_report.md"

    assert json_path.exists(), f"Missing {json_path}"
    assert report_path.exists(), f"Missing {report_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        personas = json.load(f)

    with open(report_path, "r", encoding="utf-8") as f:
        report_text = f.read()

    results = {
        "passed_checks": [],
        "failed_checks": [],
        "table_3_2_discrepancies": [],
        "composite_discrepancies": [],
    }

    # 1. Total Personas
    if len(personas) == 100:
        results["passed_checks"].append("Total personas == 100")
    else:
        results["failed_checks"].append(f"Total personas: {len(personas)} != 100")

    # 2. Demographic Balances
    sex_c = Counter(p["demographics"]["sex"] for p in personas)
    if sex_c == {0: 50, 1: 50}:
        results["passed_checks"].append("Sex 50/50 balance matches report")
    else:
        results["failed_checks"].append(f"Sex imbalance: {sex_c}")

    age_tiers = Counter()
    for p in personas:
        a = p["demographics"]["age"]
        if 18 <= a <= 39: age_tiers["18-39"] += 1
        elif 40 <= a <= 59: age_tiers["40-59"] += 1
        elif 60 <= a <= 79: age_tiers["60-79"] += 1
        elif a >= 80: age_tiers["80+"] += 1
    if age_tiers == {"18-39": 15, "40-59": 45, "60-79": 32, "80+": 8}:
        results["passed_checks"].append("Age tiers (15/45/32/8) match report Table 3.1")
    else:
        results["failed_checks"].append(f"Age tier mismatch: {age_tiers}")

    eth_c = Counter(p["demographics"]["ethnicity"] for p in personas)
    exp_eth = {"Caucasian": 42, "African American": 22, "Hispanic/Latino": 18, "Asian/Pacific Islander": 14, "Native American/Multiracial": 4}
    if eth_c == exp_eth:
        results["passed_checks"].append("Ethnicities match report Table 3.1")
    else:
        results["failed_checks"].append(f"Ethnicity mismatch: {eth_c}")

    # 3. 4-Quadrant Dissected Categories
    cat_c = Counter(p["feedback_evaluation"]["dissected_category"] for p in personas)
    exp_cat = {"UI/UX Friction": 31, "Software Bug": 29, "Biomarker Data Gap": 20, "Model Generalization Concern": 20}
    if cat_c == exp_cat:
        results["passed_checks"].append("4-Quadrant Feedback Categories (31/29/20/20) match report exactly")
    else:
        results["failed_checks"].append(f"Category mismatch: {cat_c}")

    # 4. Completion Status
    comp_c = Counter(p["user_journey"]["completion_status"] for p in personas)
    exp_comp = {"Success": 66, "Blocked by Bug": 23, "Abandoned Due to UX Confusion": 11}
    if comp_c == exp_comp:
        results["passed_checks"].append("Completion Statuses (66/23/11) match report Section 3.4 exactly")
    else:
        results["failed_checks"].append(f"Completion status mismatch: {comp_c}")

    # 5. Section 3.4 Cohort Subsets
    by_arch = defaultdict(list)
    for p in personas:
        by_arch[p["archetype"]].append(p)

    ciso_blocked = sum(1 for p in by_arch["Administrator: Hospital IT Security & HIPAA Officer"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    np_blocked = sum(1 for p in by_arch["Clinician: Cardiac Care Nurse Practitioner"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    diabetic_blocked = sum(1 for p in by_arch["Patient: Diabetic Silent Ischemia"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    ed_blocked = sum(1 for p in by_arch["Clinician: Emergency Department Attending"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    female_blocked = sum(1 for p in by_arch["Patient: Female Atypical Microvascular Angina"] if p["user_journey"]["completion_status"] == "Blocked by Bug")
    geriatric_abandoned = sum(1 for p in by_arch["Patient: Geriatric Multi-Morbidity"] if p["user_journey"]["completion_status"] == "Abandoned Due to UX Confusion")
    acute_abandoned = sum(1 for p in by_arch["Patient: Acute Chest Pain (High Risk)"] if p["user_journey"]["completion_status"] == "Abandoned Due to UX Confusion")

    if (ciso_blocked == 7 and np_blocked == 2 and diabetic_blocked == 6 and
        ed_blocked == 3 and female_blocked == 5 and geriatric_abandoned == 7 and acute_abandoned == 4):
        results["passed_checks"].append("Section 3.4 specific cohort failure counts match exactly (7, 2, 6, 3, 5 blocked; 7, 4 abandoned)")
    else:
        results["failed_checks"].append("Section 3.4 cohort failure count mismatch")

    # 6. Dynamic Markdown Table 3.2 Extraction & Parity Validation
    table_lines = []
    in_table = False
    for line in report_text.splitlines():
        if "PERSONA COHORT QUANTITATIVE PERFORMANCE SUMMARY" in line:
            in_table = True
            continue
        if in_table:
            table_lines.append(line)
            if line.startswith("└") or line.startswith("```"):
                if line.startswith("└"):
                    break

    if not table_lines:
        results["failed_checks"].append("Could not locate Table 3.2 in planning_committee_report.md")

    parsed_cohort_count = 0
    composite_found = False

    for line in table_lines:
        if ("│" not in line and "|" not in line) or line.startswith("├") or line.startswith("┌") or line.startswith("└"):
            continue
        delim = "│" if "│" in line else "|"
        parts = [p.strip() for p in line.split(delim)[1:-1]]
        if not parts or "ARCHETYPE COHORT" in parts[0] or "PERSONA COHORT" in parts[0]:
            continue

        cohort_name = parts[0]
        if cohort_name == "TOTALS / COMPOSITE AVERAGE":
            composite_found = True
            exp_n = int(parts[1])
            exp_u = float(parts[2].split("/")[0])
            exp_t = float(parts[3].split("/")[0])
            exp_c = float(parts[4].split("/")[0])
            exp_time = float(parts[5].rstrip("s"))

            all_n = len(personas)
            all_u = round(sum(p["feedback_evaluation"]["usability_score"] for p in personas) / all_n, 2)
            all_t = round(sum(p["feedback_evaluation"]["clinical_trust_score"] for p in personas) / all_n, 2)
            all_c = round(sum(p["feedback_evaluation"]["visual_clarity_score"] for p in personas) / all_n, 2)
            all_time = round(sum(p["user_journey"]["time_on_task_sec"] for p in personas) / all_n, 1)

            if exp_n != all_n:
                results["composite_discrepancies"].append(f"Composite Count: parsed={exp_n} vs actual={all_n}")
            if exp_u != all_u:
                results["composite_discrepancies"].append(f"Composite Usability: parsed={exp_u:.2f} vs actual={all_u:.2f} (delta={exp_u - all_u:+.2f})")
            if exp_t != all_t:
                results["composite_discrepancies"].append(f"Composite Clinical Trust: parsed={exp_t:.2f} vs actual={all_t:.2f} (delta={exp_t - all_t:+.2f})")
            if exp_c != all_c:
                results["composite_discrepancies"].append(f"Composite Visual Clarity: parsed={exp_c:.2f} vs actual={all_c:.2f} (delta={exp_c - all_c:+.2f})")
            if exp_time != all_time:
                results["composite_discrepancies"].append(f"Composite Task Time: parsed={exp_time:.1f}s vs actual={all_time:.1f}s (delta={exp_time - all_time:+.1f}s)")
            continue

        if cohort_name not in ARCHETYPE_MAP:
            results["failed_checks"].append(f"Unknown cohort in Table 3.2: {cohort_name}")
            continue

        full_name = ARCHETYPE_MAP[cohort_name]
        plist = by_arch[full_name]
        n = len(plist)
        parsed_cohort_count += 1

        exp_n = int(parts[1])
        exp_u = float(parts[2].split("/")[0])
        exp_t = float(parts[3].split("/")[0])
        exp_c = float(parts[4].split("/")[0])
        exp_time = float(parts[5].rstrip("s"))
        succ_match = re.search(r"\((\d+)/(\d+)\)", parts[6])
        exp_succ_cnt = int(succ_match.group(1)) if succ_match else None
        exp_issue = parts[7]

        act_u = round(sum(p["feedback_evaluation"]["usability_score"] for p in plist) / n, 2)
        act_t = round(sum(p["feedback_evaluation"]["clinical_trust_score"] for p in plist) / n, 2)
        act_c = round(sum(p["feedback_evaluation"]["visual_clarity_score"] for p in plist) / n, 2)
        act_time = round(sum(p["user_journey"]["time_on_task_sec"] for p in plist) / n, 1)
        act_succ_cnt = sum(1 for p in plist if p["user_journey"]["completion_status"] == "Success")
        act_issue = Counter(p["feedback_evaluation"]["dissected_category"] for p in plist).most_common(1)[0][0]

        row_errors = []
        if exp_n != n:
            row_errors.append(f"Count: parsed={exp_n} vs actual={n}")
        if exp_u != act_u:
            row_errors.append(f"Usability: parsed={exp_u:.2f} vs actual={act_u:.2f} (delta={exp_u - act_u:+.2f})")
        if exp_t != act_t:
            row_errors.append(f"Trust: parsed={exp_t:.2f} vs actual={act_t:.2f} (delta={exp_t - act_t:+.2f})")
        if exp_c != act_c:
            row_errors.append(f"Clarity: parsed={exp_c:.2f} vs actual={act_c:.2f} (delta={exp_c - act_c:+.2f})")
        if exp_time != act_time:
            row_errors.append(f"Task Time: parsed={exp_time:.1f}s vs actual={act_time:.1f}s (delta={exp_time - act_time:+.1f}s)")
        if exp_succ_cnt is not None and exp_succ_cnt != act_succ_cnt:
            row_errors.append(f"Success Count: parsed={exp_succ_cnt} vs actual={act_succ_cnt}")
        if exp_issue != act_issue and not ("Model" in exp_issue and "Model" in act_issue):
            row_errors.append(f"Primary Issue: parsed={exp_issue} vs actual={act_issue}")

        if row_errors:
            results["table_3_2_discrepancies"].append({
                "cohort": cohort_name,
                "errors": row_errors,
            })

    if parsed_cohort_count == 11:
        results["passed_checks"].append("Table 3.2 dynamic extraction parsed all 11 cohorts successfully")
    else:
        results["failed_checks"].append(f"Table 3.2 parsed {parsed_cohort_count} cohorts (expected 11)")

    if composite_found and not results["composite_discrepancies"]:
        results["passed_checks"].append("Table 3.2 Composite row matches empirical dataset exactly")
    elif not composite_found:
        results["failed_checks"].append("Table 3.2 missing composite row")

    # 8. Verbatim Quotes Audit
    p_by_id = {p["persona_id"]: p for p in personas}
    check_ids = ["PERS-001", "PERS-016", "PERS-040", "PERS-053", "PERS-061", "PERS-069", "PERS-075", "PERS-081", "PERS-086", "PERS-094"]
    quote_matches = 0
    for pid in check_ids:
        p = p_by_id.get(pid)
        if not p:
            results["failed_checks"].append(f"Missing persona {pid}")
            continue
        quote_fragment = p["feedback_evaluation"]["verbatim_quote"][:40]
        if quote_fragment in report_text:
            quote_matches += 1
        else:
            results["failed_checks"].append(f"Quote fragment for {pid} not found in report: {quote_fragment}")

    if quote_matches == len(check_ids):
        results["passed_checks"].append(f"All {quote_matches} representative verbatim quotes in Section 3.5 match personas_100.json")

    return results

if __name__ == "__main__":
    res = run_cross_verification()
    print("================ INDEPENDENT CROSS-VERIFICATION AUDIT ================")
    print(f"\n[PASSED CHECKS: {len(res['passed_checks'])}]")
    for p in res["passed_checks"]:
        print(f"  ✓ {p}")

    print(f"\n[FAILED GLOBAL CHECKS: {len(res['failed_checks'])}]")
    for f in res["failed_checks"]:
        print(f"  ✗ {f}")

    print(f"\n[TABLE 3.2 COHORT DISCREPANCIES: {len(res['table_3_2_discrepancies'])} of 11 cohorts failing]")
    for d in res["table_3_2_discrepancies"]:
        print(f"  ✗ Cohort: {d['cohort']}")
        for err in d["errors"]:
            print(f"      - {err}")

    print(f"\n[COMPOSITE ROW DISCREPANCIES: {len(res['composite_discrepancies'])} failing]")
    for c in res["composite_discrepancies"]:
        print(f"  ✗ {c}")

    if res["table_3_2_discrepancies"] or res["composite_discrepancies"] or res["failed_checks"]:
        print("\nOVERALL VERIFICATION: DISCORDANCE DETECTED (REJECT)")
        sys.exit(1)
    else:
        print("\nOVERALL VERIFICATION: 100% ALIGNED (APPROVE)")
        sys.exit(0)
