import unittest

from dexterous_hand_news import DATE_STR, has_required_content, is_relevant_robotics_item, md_to_html


class DexterousHandNewsTests(unittest.TestCase):
    def test_relevance_accepts_dexterous_hand_topic(self):
        region = {"emoji": "🔬"}
        self.assertTrue(is_relevant_robotics_item(region, "New tactile sensor improves dexterous robot hand manipulation"))

    def test_relevance_rejects_generic_humanoid_story(self):
        region = {"emoji": "🔬"}
        self.assertFalse(is_relevant_robotics_item(region, "Humanoid robot begins warehouse trial"))

    def test_global_section_requires_at_least_five_items(self):
        lines = ["## 🌍 全球灵巧手 / Global Dexterous Hands"]
        for index in range(5):
            lines.append(f"- **[{DATE_STR}] Source {index} — Item {index}**")
        self.assertTrue(has_required_content("\n".join(lines)))
        self.assertFalse(has_required_content("\n".join(lines[:-1])))

    def test_html_keeps_responsive_theme_controls(self):
        markdown = f"""# Dexterous Hand News | {DATE_STR}
> Current dexterous-hand news.
## 🌍 全球灵巧手 / Global Dexterous Hands
- **[{DATE_STR}] Source — Tactile robot hand**
  English: A factual summary about a tactile robot hand.
  中文：总结：关于触觉机器人手的事实摘要。
  📰 [Source](https://example.com/article)
"""
        page = md_to_html(markdown)
        self.assertIn("Dexterous Hand News", page)
        self.assertIn('id="themeBtn"', page)
        self.assertIn("width:calc(100vw - 48px)", page)


if __name__ == "__main__":
    unittest.main()
