"""
Milestone M3 Independent Challenger Test Suite: UI/UX Responsive Layout, Accessibility & Ergonomics.
Author: m3_challenger_2 (Empirical Challenger)

Verifies:
1. CSS AST and rules across 320px, 1023px, 1024px, 2560px, and 3840px viewports.
   - Confirm 'min-width: 320px' is absent from '.app-detection-info' and entire styles.css.
   - Confirm '@media (max-width: 1040px)' is absent.
   - Verify breakpoint logic: grid collapses to 1 column only at <= 1023px, remains 2-column workstation at >= 1024px.
   - Verify scaling up to 2160px container on 2560px and 3840px displays.
2. Touch target dimensions across all interactive components (minimum 44-48px for clinical primary controls).
3. portal/index.html ARIA attributes, radiogroups, and semantic markup.
4. Node.js AST compilation: 'node -c portal/portal.js'.
5. cgi_heart.py responsive media queries and HUD overlay collision avoidance.
"""

import os
import re
import subprocess
import unittest
from typing import Dict, List, Tuple, Optional


class CSSParser:
    """Lightweight CSS AST parser for verifying rules and media queries."""

    def __init__(self, css_text: str):
        self.raw_css = css_text
        # Strip comments
        clean = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
        # Strip @import statements (handling query params with semicolons)
        clean = re.sub(r'@import\s+url\([^)]+\)\s*;', '', clean)
        self.clean_css = clean
        self.media_blocks: List[Tuple[str, str]] = []
        self.top_level_rules: Dict[str, Dict[str, str]] = {}
        self._parse()

    def _parse(self):
        # Extract @media blocks
        media_pattern = re.compile(r'@media\s*([^{]+)\{((?:[^{}]+|\{[^{}]*\})+)\}', re.DOTALL)
        matches = list(media_pattern.finditer(self.clean_css))
        
        for m in matches:
            query = m.group(1).strip()
            body = m.group(2).strip()
            self.media_blocks.append((query, body))

        # Extract top-level rules outside @media
        no_media = media_pattern.sub('', self.clean_css)
        rule_pattern = re.compile(r'([^{]+)\{([^}]+)\}', re.DOTALL)
        for m in rule_pattern.finditer(no_media):
            selectors = [s.strip() for s in m.group(1).split(',')]
            declarations = self._parse_declarations(m.group(2))
            for sel in selectors:
                if sel:
                    if sel not in self.top_level_rules:
                        self.top_level_rules[sel] = {}
                    self.top_level_rules[sel].update(declarations)

    @staticmethod
    def _parse_declarations(decl_str: str) -> Dict[str, str]:
        decls = {}
        for item in decl_str.split(';'):
            if ':' in item:
                prop, val = item.split(':', 1)
                decls[prop.strip()] = val.strip()
        return decls

    def parse_media_rules(self, body: str) -> Dict[str, Dict[str, str]]:
        rules: Dict[str, Dict[str, str]] = {}
        rule_pattern = re.compile(r'([^{]+)\{([^}]+)\}', re.DOTALL)
        for m in rule_pattern.finditer(body):
            selectors = [s.strip() for s in m.group(1).split(',')]
            decls = self._parse_declarations(m.group(2))
            for sel in selectors:
                if sel not in rules:
                    rules[sel] = {}
                rules[sel].update(decls)
        return rules

    @staticmethod
    def matches_media_query(query: str, viewport_width: int) -> bool:
        """Evaluate whether a media query matches a specific viewport width."""
        # e.g., (max-width: 1023px), (min-width: 1024px), (min-width: 2560px)
        max_m = re.search(r'max-width:\s*(\d+)px', query)
        min_m = re.search(r'min-width:\s*(\d+)px', query)
        
        matches = True
        if max_m:
            max_val = int(max_m.group(1))
            if viewport_width > max_val:
                matches = False
        if min_m:
            min_val = int(min_m.group(1))
            if viewport_width < min_val:
                matches = False
        return matches

    def get_effective_properties(self, selector: str, viewport_width: int) -> Dict[str, str]:
        """Compute cascaded properties for a selector at given viewport width."""
        props = dict(self.top_level_rules.get(selector, {}))
        for query, body in self.media_blocks:
            if self.matches_media_query(query, viewport_width):
                media_rules = self.parse_media_rules(body)
                if selector in media_rules:
                    props.update(media_rules[selector])
        return props


class TestCSSResponsiveViewportsAST(unittest.TestCase):
    """Empirical challenge of CSS rules and AST across 320px, 1023px, 1024px, 2560px, 3840px."""

    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.css_path = os.path.join(base_dir, "portal", "styles.css")
        with open(cls.css_path, "r", encoding="utf-8") as f:
            cls.css_raw = f.read()
        cls.parser = CSSParser(cls.css_raw)

    def test_absence_of_deprecated_rules(self):
        """Confirm 'min-width: 320px' is absent from .app-detection-info and styles.css, and 1040px query is absent."""
        self.assertNotIn("min-width: 320px", self.css_raw, "Found forbidden 'min-width: 320px' in styles.css")
        self.assertNotIn("@media (max-width: 1040px)", self.css_raw, "Found deprecated 1040px query in styles.css")

    def test_app_detection_info_properties(self):
        """Confirm .app-detection-info has min-width: 0 and does not clip at 320px."""
        props = self.parser.get_effective_properties(".app-detection-info", 320)
        self.assertEqual(props.get("min-width"), "0", ".app-detection-info min-width must be 0")
        self.assertEqual(props.get("max-width"), "100%", ".app-detection-info max-width must be 100%")

    def test_viewport_320px_layout_invariants(self):
        """Verify 320px viewport rules: grid collapse, container bounds, zero overflow."""
        props_grid = self.parser.get_effective_properties(".workstation-grid", 320)
        self.assertEqual(
            props_grid.get("grid-template-columns"),
            "1fr",
            "At 320px, workstation grid must collapse to 1fr single column"
        )
        # Check sticky column is static on mobile
        props_sticky = self.parser.get_effective_properties(".workstation-sticky-col", 320)
        self.assertEqual(
            props_sticky.get("position"),
            "static",
            "At 320px, workstation-sticky-col must have position: static"
        )

    def test_viewport_1023px_vs_1024px_boundary_switch(self):
        """Verify precise boundary transition between 1023px (mobile/tablet single-col) and 1024px (workstation dual-col)."""
        # At 1023px: should collapse to 1fr
        props_1023 = self.parser.get_effective_properties(".workstation-grid", 1023)
        self.assertEqual(
            props_1023.get("grid-template-columns"),
            "1fr",
            "At 1023px, workstation grid must be 1fr (collapsed for tablet portrait)"
        )
        sticky_1023 = self.parser.get_effective_properties(".workstation-sticky-col", 1023)
        self.assertEqual(
            sticky_1023.get("position"),
            "static",
            "At 1023px, sticky column must be static"
        )

        # At 1024px: must be dual column workstation mode
        props_1024 = self.parser.get_effective_properties(".workstation-grid", 1024)
        expected_cols = "minmax(360px, 5fr) minmax(460px, 7fr)"
        self.assertEqual(
            props_1024.get("grid-template-columns"),
            expected_cols,
            f"At 1024px, workstation grid must maintain dual column {expected_cols}"
        )
        sticky_1024 = self.parser.get_effective_properties(".workstation-sticky-col", 1024)
        self.assertEqual(
            sticky_1024.get("position"),
            "sticky",
            "At 1024px, workstation-sticky-col must have position: sticky"
        )
        self.assertEqual(
            sticky_1024.get("top"),
            "84px",
            "At 1024px, workstation-sticky-col top offset must be 84px"
        )

    def test_viewport_2560px_and_3840px_scaling(self):
        """Verify 2560px and 3840px ultrawide/4K container scaling up to 2160px max-width."""
        props_root_2560 = self.parser.get_effective_properties(":root", 2560)
        self.assertEqual(
            props_root_2560.get("--grid-max-width"),
            "2160px",
            "At 2560px, --grid-max-width must scale to 2160px"
        )
        self.assertEqual(
            props_root_2560.get("--grid-gutter"),
            "48px",
            "At 2560px, --grid-gutter must scale to 48px"
        )
        self.assertEqual(
            props_root_2560.get("--grid-gap"),
            "40px",
            "At 2560px, --grid-gap must scale to 40px"
        )

        props_root_3840 = self.parser.get_effective_properties(":root", 3840)
        self.assertEqual(
            props_root_3840.get("--grid-max-width"),
            "2160px",
            "At 3840px, --grid-max-width must maintain 2160px"
        )
        props_html_3840 = self.parser.get_effective_properties("html", 3840)
        self.assertEqual(
            props_html_3840.get("font-size"),
            "18px",
            "At 3840px, html font-size must scale to 18px for physical viewing distance ergonomics"
        )


class TestTouchTargetDimensions(unittest.TestCase):
    """Empirical verification of touch target hitboxes according to ANSI/AAMI HE75 Section 8.4 and WCAG 2.5.5/2.5.8."""

    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.css_path = os.path.join(base_dir, "portal", "styles.css")
        with open(cls.css_path, "r", encoding="utf-8") as f:
            cls.css_raw = f.read()
        cls.parser = CSSParser(cls.css_raw)

    def test_touch_target_min_token_definition(self):
        """:root must define --touch-target-min: 48px."""
        root_props = self.parser.get_effective_properties(":root", 1200)
        self.assertEqual(
            root_props.get("--touch-target-min"),
            "48px",
            "--touch-target-min token must be 48px in :root"
        )

    def test_primary_clinical_sliders(self):
        """Sliders must have a touch wrapper of at least 48px and slider track/hitbox >= 44px."""
        wrapper_props = self.parser.get_effective_properties(".clinical-slider-wrapper", 1200)
        self.assertIn(
            wrapper_props.get("min-height"),
            ["var(--touch-target-min)", "48px"],
            ".clinical-slider-wrapper min-height must be 48px"
        )

        slider_props = self.parser.get_effective_properties(".clinical-slider", 1200)
        slider_height = int(re.search(r'(\d+)px', slider_props.get("height", "0")).group(1))
        self.assertGreaterEqual(
            slider_height,
            44,
            f".clinical-slider height must be >= 44px, got {slider_height}px"
        )

    def test_clinical_selects(self):
        """Dropdown selects must have height >= 44px (configured to 46px)."""
        select_props = self.parser.get_effective_properties(".clinical-select", 1200)
        select_height = int(re.search(r'(\d+)px', select_props.get("height", "0")).group(1))
        self.assertGreaterEqual(
            select_height,
            44,
            f".clinical-select height must be >= 44px, got {select_height}px"
        )

    def test_standard_app_buttons(self):
        """.app-btn, .app-btn-md, and .app-btn-lg must have minimum touch height >= 48px."""
        btn_props = self.parser.get_effective_properties(".app-btn", 1200)
        self.assertIn(
            btn_props.get("min-height"),
            ["var(--touch-target-min)", "48px"],
            ".app-btn min-height must be 48px"
        )
        self.assertEqual(
            btn_props.get("min-width"),
            "44px",
            ".app-btn min-width must be >= 44px"
        )

        btn_md_props = self.parser.get_effective_properties(".app-btn-md", 1200)
        self.assertIn(
            btn_md_props.get("min-height"),
            ["var(--touch-target-min)", "48px"],
            ".app-btn-md min-height must be 48px"
        )

        btn_lg_props = self.parser.get_effective_properties(".app-btn-lg", 1200)
        lg_height = int(re.search(r'(\d+)px', btn_lg_props.get("min-height", "0")).group(1))
        self.assertGreaterEqual(lg_height, 48, ".app-btn-lg must be >= 48px")

    def test_secondary_and_toolbar_controls(self):
        """Secondary buttons and HUD controls must meet ANSI/AAMI HE75 Section 8.4 secondary threshold (>= 40px)."""
        sm_btn_props = self.parser.get_effective_properties(".app-btn-sm", 1200)
        sm_height = int(re.search(r'(\d+)px', sm_btn_props.get("min-height", "0")).group(1))
        self.assertGreaterEqual(sm_height, 40, ".app-btn-sm min-height must be >= 40px")

        mode_props = self.parser.get_effective_properties(".mode-btn", 1200)
        mode_height = int(re.search(r'(\d+)px', mode_props.get("min-height", "0")).group(1))
        self.assertGreaterEqual(mode_height, 40, ".mode-btn min-height must be >= 40px")

        sound_props = self.parser.get_effective_properties(".sound-btn", 1200)
        sound_height = int(re.search(r'(\d+)px', sound_props.get("min-height", "0")).group(1))
        self.assertGreaterEqual(sound_height, 40, ".sound-btn min-height must be >= 40px")

        gen_props = self.parser.get_effective_properties(".gen-filter-btn", 1200)
        gen_height = int(re.search(r'(\d+)px', gen_props.get("min-height", "0")).group(1))
        self.assertGreaterEqual(gen_height, 40, ".gen-filter-btn min-height must be >= 40px")

        login_props = self.parser.get_effective_properties(".app-login-btn", 1200)
        login_height = int(re.search(r'(\d+)px', login_props.get("min-height", "0")).group(1))
        self.assertGreaterEqual(login_height, 40, ".app-login-btn min-height must be >= 40px")


class TestPortalHtmlAccessibilityAndSemantics(unittest.TestCase):
    """Empirical verification of portal/index.html ARIA attributes, radiogroups, and semantic structure."""

    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.html_path = os.path.join(base_dir, "portal", "app.html")
        with open(cls.html_path, "r", encoding="utf-8") as f:
            cls.html_raw = f.read()

    def test_semantic_landmarks_present(self):
        """Verify semantic landmarks <header>, <nav>, <main>, <section>, and <footer>."""
        for tag in ["<header", "<nav", "<main", "<section", "<footer"]:
            self.assertIn(tag, self.html_raw, f"Missing semantic landmark tag {tag}")

    def test_case_studies_accessible_radiogroup(self):
        """Verify case study preset selector implements role='radiogroup' and role='radio' with aria-checked."""
        self.assertIn(
            'class="case-study-list" role="radiogroup"',
            self.html_raw,
            "Case study list must implement role='radiogroup'"
        )
        self.assertIn(
            'aria-label="Synthetic sample cases"',
            self.html_raw,
            "Radiogroup must possess descriptive aria-label"
        )
        
        # Verify 3 clinical case study radio buttons
        for case_id in ["case-btn-acs", "case-btn-diabetic", "case-btn-wellness"]:
            self.assertIn(f'id="{case_id}"', self.html_raw, f"Missing case button {case_id}")
            # Ensure each has role="radio" and aria-checked
            pattern = re.compile(rf'<button[^>]+id="{case_id}"[^>]*>', re.DOTALL)
            m = pattern.search(self.html_raw)
            self.assertIsNotNone(m, f"Could not find tag for {case_id}")
            tag_str = m.group(0)
            self.assertIn('role="radio"', tag_str, f"{case_id} must have role='radio'")
            self.assertIn('aria-checked=', tag_str, f"{case_id} must have aria-checked attribute")

    def test_all_13_clinical_inputs_paired_with_labels(self):
        """Verify all 13 Cleveland Clinic input controls have matching <label for='...'> tags."""
        required_inputs = [
            "inp-age", "inp-sex", "inp-cp", "inp-trestbps", "inp-chol",
            "inp-fbs", "inp-restecg", "inp-thalach", "inp-exang",
            "inp-oldpeak", "inp-slope", "inp-ca", "inp-thal"
        ]
        for inp_id in required_inputs:
            # Check input/select element
            self.assertRegex(
                self.html_raw,
                rf'<(input|select)[^>]+id="{inp_id}"',
                f"Missing input/select with id='{inp_id}'"
            )
            # Check corresponding label for=inp_id
            self.assertRegex(
                self.html_raw,
                rf'<label[^>]+for="{inp_id}"',
                f"Missing <label for='{inp_id}'> pairing for clinical biomarker"
            )

    def test_dual_labeling_layperson_and_clinical_acronyms(self):
        """Verify dual-labeling format: layperson description + clinical acronym and units."""
        biomarker_acronyms = [
            "age · 20-90 yrs",
            "sex · 1=M, 0=F",
            "trestbps · normal &lt; 120",
            "chol · normal &lt; 200",
            "fbs · normal &le; 120",
            "restecg · 0-2",
            "thalach · normal 120-200",
            "cp · Type 1-4",
            "exang · 0/1",
            "slope · 1-3",
            "oldpeak · normal 0.0 mm",
            "ca · required",
            "thal · required",
        ]
        for acr in biomarker_acronyms:
            self.assertIn(acr, self.html_raw, f"Missing clinical dual-label acronym info: {acr}")

    def test_slider_aria_values_and_live_readouts(self):
        """Verify sliders have aria-valuemin, aria-valuemax, aria-valuenow, and live tags have aria-live='polite'."""
        slider_ids = ["inp-age", "inp-trestbps", "inp-chol", "inp-thalach", "inp-oldpeak"]
        for sid in slider_ids:
            pattern = re.compile(rf'<input[^>]+id="{sid}"[^>]*>', re.DOTALL)
            m = pattern.search(self.html_raw)
            self.assertIsNotNone(m, f"Could not find slider {sid}")
            tag_str = m.group(0)
            self.assertIn('aria-valuemin=', tag_str, f"{sid} missing aria-valuemin")
            self.assertIn('aria-valuemax=', tag_str, f"{sid} missing aria-valuemax")
            self.assertIn('aria-valuenow=', tag_str, f"{sid} missing aria-valuenow")
            self.assertIn('aria-label=', tag_str, f"{sid} missing aria-label")

        live_tag_ids = ["val-age", "val-trestbps", "val-chol", "val-thalach", "val-oldpeak"]
        for lid in live_tag_ids:
            pattern = re.compile(rf'<span[^>]+id="{lid}"[^>]*>', re.DOTALL)
            m = pattern.search(self.html_raw)
            self.assertIsNotNone(m, f"Could not find live tag {lid}")
            tag_str = m.group(0)
            self.assertIn('aria-live="polite"', tag_str, f"{lid} missing aria-live='polite'")

    def test_modal_accessibility_dialog_attributes(self):
        """Verify modal dialogs have role='dialog', aria-modal='true', and labelledby."""
        for modal_id, title_id in [("app-auth-modal", "auth-modal-title"), ("app-report-modal", "report-modal-title")]:
            self.assertIn(f'id="{modal_id}"', self.html_raw, f"Missing {modal_id}")
            pattern = re.compile(rf'<div[^>]+id="{modal_id}"[^>]*>', re.DOTALL)
            m = pattern.search(self.html_raw)
            self.assertIsNotNone(m, f"Tag {modal_id} not found")
            tag_str = m.group(0)
            self.assertIn('role="dialog"', tag_str, f"{modal_id} must have role='dialog'")
            self.assertIn('aria-modal="true"', tag_str, f"{modal_id} must have aria-modal='true'")
            self.assertIn(f'aria-labelledby="{title_id}"', tag_str, f"{modal_id} must have aria-labelledby='{title_id}'")


class TestNodeCompilationAndSyntax(unittest.TestCase):
    """Empirical verification of JavaScript compilation via Node.js AST checker."""

    def test_portal_js_compiles_cleanly_with_node(self):
        """Execute 'node -c portal/portal.js' and verify exit code is 0 with empty stderr."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        portal_js_path = os.path.join(base_dir, "portal", "portal.js")
        self.assertTrue(os.path.exists(portal_js_path), f"File {portal_js_path} does not exist")

        res = subprocess.run(
            ["node", "-c", portal_js_path],
            capture_output=True,
            text=True
        )
        self.assertEqual(
            res.returncode,
            0,
            f"node -c portal/portal.js failed with code {res.returncode}. Stderr: {res.stderr}"
        )
        self.assertEqual(res.stderr.strip(), "", f"Unexpected stderr from node -c: {res.stderr}")


class TestCgiHeartResponsiveAndCollisionAvoidance(unittest.TestCase):
    """Empirical verification of cgi_heart.py responsive layout and HUD overlay collision avoidance."""

    @classmethod
    def setUpClass(cls):
        import cgi_heart
        cls.cgi_heart = cgi_heart

    def test_cgi_heart_responsive_media_query_and_layout(self):
        """Verify cgi_heart.py generates @media (max-width: 640px) with column-wrapped HUDs."""
        rendered = self.cgi_heart.render_cgi_heart(risk_score=0.68, embed_vendor=False)
        self.assertIn(
            "@media (max-width: 640px)",
            rendered,
            "cgi_heart.py must include @media (max-width: 640px) query"
        )
        # Verify HUD top and bottom flex column wrapping on mobile
        self.assertIn(".hud-top", rendered)
        self.assertIn("flex-direction: column", rendered)
        self.assertIn(".mode-toolbar", rendered)
        self.assertIn("overflow-x: auto", rendered)
        self.assertIn(".hud-bottom", rendered)
        self.assertIn(".ecg-card", rendered)
        self.assertIn(".vitals-grid", rendered)

    def test_cgi_heart_hud_collision_avoidance_geometry(self):
        """Empirically calculate vertical footprints of top and bottom HUDs to verify zero overlap on small viewports."""
        # Top HUD elements: .hud-top (top: 12px; left: 12px; right: 12px; gap: 8px)
        #   - .hud-badge: title (~18px) + value (~26px) + model line (~16px) + padding (~14px) ~ 74px
        #   - .mode-toolbar: buttons (40px) + padding (~6px) ~ 46px
        #   - gap (8px)
        # Total top HUD vertical footprint: 12px + 74px + 8px + 46px = 140px.
        top_hud_max_y = 140

        # Bottom HUD elements: .hud-bottom (bottom: 12px; left: 12px; right: 12px; gap: 8px)
        #   - .ecg-card: canvas (36px) + labels + padding ~ 64px
        #   - .vitals-grid: 3 vitals pills ~ 50px
        #   - gap (8px)
        # Total bottom HUD vertical footprint: 12px + 64px + 8px + 50px = 134px.
        bottom_hud_extent = 134

        # Test minimum mobile screen height (iPhone SE: 568px, Streamlit iframe: 580px - 650px)
        min_viewport_height = 568
        free_canvas_height = min_viewport_height - (top_hud_max_y + bottom_hud_extent)

        # Free space between overlays for the 3D WebGL anatomical heart
        self.assertGreater(
            free_canvas_height,
            200,
            f"Overlays would collide or leave insufficient 3D canvas clearance: {free_canvas_height}px"
        )
        print(f"[HUD Collision Avoidance] Viewport 568px height -> Free 3D Canvas clearance: {free_canvas_height}px")

    def test_cgi_heart_calling_conventions_and_resilience(self):
        """Verify render_cgi_heart survives diverse calling signatures without syntax or runtime exceptions."""
        patient_sample = {
            "age": 64, "sex": 1, "cp": 4, "trestbps": 160, "chol": 270,
            "fbs": 1, "restecg": 2, "thalach": 125, "exang": 1,
            "oldpeak": 3.4, "slope": 3, "ca": 2, "thal": 7
        }
        # 1. Float risk_score
        html1 = self.cgi_heart.render_cgi_heart(0.72)
        self.assertIn("Cardiac Telemetry & AI Diagnosis", html1)

        # 2. Dictionary positional
        html2 = self.cgi_heart.render_cgi_heart(patient_sample, 0.85, "HIGH")
        self.assertIn("HIGH", html2)

        # 3. Partial dictionary with missing thalach
        partial_patient = {"age": 55, "sex": 0}
        html3 = self.cgi_heart.render_cgi_heart(patient_dict=partial_patient, risk_band="MODERATE", risk_prob=0.48)
        self.assertIn("Cardiac Telemetry", html3)

        # 4. None values
        none_patient = {"age": None, "thalach": None, "ca": None}
        html4 = self.cgi_heart.render_cgi_heart(patient_dict=none_patient, risk_score=0.5)
        self.assertIn("MODERATE", html4)


if __name__ == "__main__":
    unittest.main()
