import unittest

from designer_integration import design_geometry
from engineering_drawings import isometric_svg, plan_svg, section_svg, standalone_html


class EngineeringDrawingTests(unittest.TestCase):
    def setUp(self):
        self.inputs, self.model, _ = design_geometry(
            125000, 15, 1.5, 2.5, 1.16,
            layout={"pumpSide": "East", "pumpLength": 12, "pumpWidth": 8,
                    "drainageWells": 4, "designFlowM3h": 150},
        )

    def test_sheets_are_static_svg_with_shared_geometry(self):
        plan = plan_svg(self.inputs, self.model)
        sections = section_svg(self.inputs, self.model)
        concept = isometric_svg(self.inputs, self.model)
        self.assertIn("125,000.0", plan)
        self.assertIn("SECTION A–A", sections)
        self.assertIn("125,000.0", concept)
        self.assertTrue(all("<svg" in sheet for sheet in (plan, sections, concept)))

    def test_offline_package_has_no_external_scripts(self):
        report = standalone_html(self.inputs, self.model)
        self.assertIn("PTES engineering drawing package", report)
        self.assertNotIn("<script", report)


if __name__ == "__main__":
    unittest.main()
