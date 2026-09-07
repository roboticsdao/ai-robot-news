import unittest

from dexterous_hand_news import DATE_STR, has_required_content, is_relevant_robotics_item, md_to_html


class DexterousHandNewsTests(unittest.TestCase):
    def test_relevance_accepts_dexterous_hand_topic(self):
        region = {"emoji": "🔬"}
        self.assertTrue(is_relevant_robotics_item(region, "New tactile sensor improves dexterous robot hand manipulation"))

    def test_relevance_rejects_generic_humanoid_story(self):
        region = {"emoji": "🔬"}
        self.assertFalse(is_relevant_robotics_item(region, "Humanoid robot begins warehouse trial"))

    def test_required_sections_need_three_items_each(self):
        sections = []
        for heading in ("🇯🇵 日本 / Japan", "🇺🇸 美国 / United States", "🇨🇳 中国 / China", "🔬 全球研究与产业 / Global Research & Industry"):
            sections.append(f"## {heading}")
            for index in range(3):
                sections.append(f"- **[{DATE_STR}] Source {index} — Item {index}**")
        self.assertTrue(has_required_content("\n".join(sections)))

    def test_html_keeps_responsive_theme_controls(self):
        markdown = f"""# Dexterous Hand News | {DATE_STR}
> Current dexterous-hand news.
## 🔬 全球研究与产业 / Global Research & Industry
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
