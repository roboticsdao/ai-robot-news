import unittest

import ai_robot_news_automation as news


class DigestValidationTests(unittest.TestCase):
    def test_shortfall_is_available_content_not_a_system_failure(self):
        digest='\n'.join(f'## {region}\n- **[{news.DATE_STR}] A source story**' for region in ['🇺🇸 United States','🇨🇳 China','🇯🇵 Japan','🤖 Humanoid Robotics'])
        self.assertTrue(news.has_required_content(digest))

    def test_stale_stories_are_not_relabelled_as_fresh(self):
        digest='\n'.join(f'## {region}\n- **[2020.01.01] A source story**' for region in ['🇺🇸 United States','🇨🇳 China','🇯🇵 Japan','🤖 Humanoid Robotics'])
        self.assertFalse(news.has_required_content(digest))

    def test_empty_section_notice_stays_in_its_section(self):
        page=news.md_to_html('> Original disclaimer\n## 🇯🇵 Japan\n> No new readable article\n## 🇺🇸 US\n- **['+news.DATE_STR+'] Example**\n  English: Source facts.')
        self.assertIn('Original disclaimer',page)
        self.assertIn('No new readable article',page)
        self.assertIn('Japan',page)

    def test_invalid_or_future_dates_are_not_treated_as_today(self):
        for date in ('2026.99.99', '2099.01.01'):
            self.assertFalse(news.has_recent_content(f'- **[{date}] Source story**'))
    def test_local_and_chinese_text_of_same_story_do_not_compare(self):
        body = "Honda announced new robot hardware for an experiment on a space station with twelve sensors and a precision arm."
        digest = f"- **[{news.DATE_STR}] Honda experiment**\n  English: {body}\n  中文：总结：{body}"
        self.assertEqual([], news.digest_quality_issues(digest))

    def test_different_stories_with_repeated_summaries_still_fail(self):
        body = "A company announced new hardware for an experiment on a space station with twelve sensors and a precision arm."
        digest = "\n".join(f"- **[{news.DATE_STR}] {title}**\n  English: {body}" for title in ("First news", "Second news"))
        self.assertTrue(news.digest_quality_issues(digest))
