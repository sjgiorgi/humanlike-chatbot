import unittest
from unittest.mock import Mock
from ..services.post_processing import calculate_typing_delays, create_instant_display_response


class TestDelayCalculation(unittest.TestCase):
    def setUp(self):
        self.bot_config = Mock()
        self.bot_config.humanlike_delay = True
        self.bot_config.reading_words_per_minute = 250.0
        self.bot_config.reading_jitter_min = 0.1
        self.bot_config.reading_jitter_max = 0.3
        self.bot_config.reading_thinking_min = 0.2
        self.bot_config.reading_thinking_max = 0.5
        self.bot_config.writing_words_per_minute = 200.0
        self.bot_config.writing_jitter_min = 0.05
        self.bot_config.writing_jitter_max = 0.15
        self.bot_config.writing_thinking_min = 0.1
        self.bot_config.writing_thinking_max = 0.3
        self.bot_config.intra_message_delay_min = 0.1
        self.bot_config.intra_message_delay_max = 0.3
        self.bot_config.min_reading_delay = 1.0

    def test_zero_delays_when_disabled(self):
        """Test that delays are zero when humanlike_delay is disabled"""
        self.bot_config.humanlike_delay = False
        response_segments = ["Hello", "World"]
        result = calculate_typing_delays(
            "Hi", response_segments, self.bot_config)

        self.assertEqual(result['reading_time'], 0.0)
        self.assertEqual(result['min_reading_delay'], 0.0)
        for segment in result['response_segments']:
            self.assertEqual(segment['writing_delay'], 0.0)
            self.assertEqual(segment['inter_segment_delay'], 0.0)

    def test_reading_time_calculation(self):
        """Test that reading time is calculated correctly"""
        message = "Hello world this is a test message"
        response_segments = ["Response part 1", "Response part 2"]

        result = calculate_typing_delays(
            message, response_segments, self.bot_config)

        # Should have positive reading time
        self.assertGreater(result['reading_time'], 0.0)
        self.assertEqual(result['min_reading_delay'], 1.0)

        # Should have correct number of response segments
        self.assertEqual(len(result['response_segments']), 2)

        # Each segment should have positive delays
        for segment in result['response_segments']:
            self.assertGreater(segment['writing_delay'], 0.0)
            self.assertGreaterEqual(segment['inter_segment_delay'], 0.0)

    def test_create_instant_display_response(self):
        """Test the instant display response creation"""
        response_segments = ["Part 1", "Part 2", "Part 3"]
        result = create_instant_display_response(response_segments)

        self.assertEqual(result['reading_time'], 0.0)
        self.assertEqual(result['min_reading_delay'], 0.0)
        self.assertEqual(len(result['response_segments']), 3)

        for segment in result['response_segments']:
            self.assertEqual(segment['writing_delay'], 0.0)
            self.assertEqual(segment['inter_segment_delay'], 0.0)

    def test_response_segments_structure(self):
        """Test that response segments have correct structure"""
        message = "Test message"
        response_segments = ["First part", "Second part"]

        result = calculate_typing_delays(
            message, response_segments, self.bot_config)

        # Check structure
        self.assertIn('reading_time', result)
        self.assertIn('min_reading_delay', result)
        self.assertIn('response_segments', result)

        # Check response segments structure
        for segment in result['response_segments']:
            self.assertIn('content', segment)
            self.assertIn('writing_delay', segment)
            self.assertIn('inter_segment_delay', segment)

            # Content should match original
            self.assertIn(segment['content'], response_segments)

    def test_delay_ranges(self):
        """Test that delays are within expected ranges"""
        message = "A short message"  # 3 words
        response_segments = ["Response"]

        result = calculate_typing_delays(
            message, response_segments, self.bot_config)

        # Reading time should be reasonable (based on 3 words at 250 WPM)
        # base + min jitter + min thinking
        expected_min_reading = (3 * 60 / 250) + 0.1 + 0.2
        # base + max jitter + max thinking
        expected_max_reading = (3 * 60 / 250) + 0.3 + 0.5

        self.assertGreaterEqual(result['reading_time'], expected_min_reading)
        self.assertLessEqual(result['reading_time'], expected_max_reading)

        # Writing delay should be reasonable (based on response length)
        segment = result['response_segments'][0]
        response_words = len(segment['content'].split())
        expected_min_writing = (response_words * 60 / 200) + 0.05 + 0.1
        expected_max_writing = (response_words * 60 / 200) + 0.15 + 0.3

        self.assertGreaterEqual(segment['writing_delay'], expected_min_writing)
        self.assertLessEqual(segment['writing_delay'], expected_max_writing)

        # Inter-segment delay should be within range
        self.assertGreaterEqual(segment['inter_segment_delay'], 0.1)
        self.assertLessEqual(segment['inter_segment_delay'], 0.3)

    def test_empty_response_segments(self):
        """Test handling of empty response segments"""
        message = "Test"
        response_segments = []

        result = calculate_typing_delays(
            message, response_segments, self.bot_config)

        self.assertEqual(len(result['response_segments']), 0)
        # Reading time should still be calculated
        self.assertGreater(result['reading_time'], 0.0)

    def test_single_response_segment(self):
        """Test handling of single response segment"""
        message = "Test message"
        response_segments = ["Single response"]

        result = calculate_typing_delays(
            message, response_segments, self.bot_config)

        self.assertEqual(len(result['response_segments']), 1)
        segment = result['response_segments'][0]
        self.assertEqual(segment['content'], "Single response")
        self.assertGreater(segment['writing_delay'], 0.0)
        self.assertGreaterEqual(segment['inter_segment_delay'], 0.0)


if __name__ == '__main__':
    unittest.main()
