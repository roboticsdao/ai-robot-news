import unittest

from dexterous_hand_news import DATE_STR, digest_quality_issues, has_required_content, is_relevant_robotics_item, md_to_html


class DexterousHandNewsTests(unittest.TestCase):
    def test_same_story_bilingual_summary_is_not_a_duplicate(self):
        body = "Honda released new robot hands for a space station experiment with twelve sensors and a precision arm."
        digest = f"- **[{DATE_STR}] Honda experiment**\n  English: {body}\n  中文：总结：{body}"
        self.assertEqual([], digest_quality_issues(digest))

    def test_repeated_text_in_separate_stories_is_still_rejected(self):
        body = "Honda released new robot hands for a space station experiment with twelve sensors and a precision arm."
        digest = "\n".join(f"- **[{DATE_STR}] {title}**\n  English: {body}" for title in ("First news", "Second news"))
        self.assertTrue(digest_quality_issues(digest))

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
