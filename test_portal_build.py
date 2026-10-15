import unittest

from tools import build_portal as portal


class PortalTests(unittest.TestCase):
    def test_reference_is_data_not_executable_script(self):
        self.assertEqual([], portal.parse_reference('/* generated */ window.DATA={"companies":[],"news":[]};')["news"])
        with self.assertRaises(ValueError):
            portal.parse_reference('window.DATA={"companies":[],"news":[]}; alert(1)')

    def test_name_boundaries_avoid_false_company_links(self):
        for name, text in [("ATI", "US inflation slows"), ("Meta", "metal supply"), ("Apple", "Appleton expands")]:
            self.assertFalse(portal.name_matches(name, text))
        for name, text in [("ATI", "ATI releases a sensor"), ("Meta", "Meta's new model"), ("1X", "1X shows NEO"), ("智元", "智元发布新机器人")]:
            self.assertTrue(portal.name_matches(name, text))

    def test_tracking_parameters_do_not_hide_distinct_article_ids(self):
        self.assertEqual("https://example.com/story?id=42", portal.canonical_url("https://example.com/story/?id=42&utm_source=rss#section"))
        self.assertNotEqual(portal.canonical_url("https://example.com/?id=1"), portal.canonical_url("https://example.com/?id=2"))

    def test_generic_robot_words_are_not_company_names(self):
        companies = [{"id": "humanoid", "name": {"en": "Humanoid"}}, {"id": "sunday", "name": {"en": "Sunday"}}]
        self.assertEqual([], portal.company_matches("A humanoid robot was shown on Sunday", companies))
        self.assertEqual(["humanoid"], portal.company_matches("Humanoid Robotics launches HMND platform", companies))

    def test_quotes_are_not_counted_as_market_news(self):
        markdown = '- **[2026.10.15] 行情快照 / Quote — Index**\n中文：snapshot\n📰 [source](https://example.com/quote)'
        self.assertEqual([], portal.markdown_articles(markdown, "market"))

    def test_old_template_is_an_index_not_a_fabricated_summary(self):
        item = {"date": "2026.10.15", "headline": "Robot launch", "source": "Original", "url": "https://example.com/story", "summary_zh": "后续要看是否量产", "kind": "robot"}
        result = portal.merge_news([], [item], [])
        self.assertEqual("archive", result[0]["origin"])
        self.assertEqual("", result[0]["summary_zh"])


if __name__ == "__main__":
    unittest.main()
