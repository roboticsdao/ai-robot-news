import unittest

import ai_robot_news_automation as news


class DigestValidationTests(unittest.TestCase):
    def test_local_and_chinese_text_of_same_story_do_not_compare(self):
        body = "Honda announced new robot hardware for an experiment on a space station with twelve sensors and a precision arm."
        digest = f"- **[{news.DATE_STR}] Honda experiment**\n  English: {body}\n  中文：总结：{body}"
        self.assertEqual([], news.digest_quality_issues(digest))

    def test_different_stories_with_repeated_summaries_still_fail(self):
        body = "A company announced new hardware for an experiment on a space station with twelve sensors and a precision arm."
        digest = "\n".join(f"- **[{news.DATE_STR}] {title}**\n  English: {body}" for title in ("First news", "Second news"))
        self.assertTrue(news.digest_quality_issues(digest))
