import unittest
from unittest.mock import Mock

from ..services.post_processing import (
    calculate_typing_delays,
    create_instant_display_response,
)


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

        assert result["reading_time"] == 0.0
        assert result["min_reading_delay"] == 0.0
        for segment in result["response_segments"]:
            assert segment["writing_delay"] == 0.0
            assert segment["inter_segment_delay"] == 0.0

    def test_reading_time_calculation(self):
        """Test that reading time is calculated correctly"""
        message = "Hello world this is a test message"
        response_segments = ["Response part 1", "Response part 2"]

        result = calculate_typing_delays(
            message, response_segments, self.bot_config)

        # Should have positive reading time
        assert result["reading_time"] > 0.0
        assert result["min_reading_delay"] == 1.0

        # Should have correct number of response segments
        assert len(result["response_segments"]) == 2

        # Each segment should have positive delays
        for segment in result["response_segments"]:
            assert segment["writing_delay"] > 0.0
            assert segment["inter_segment_delay"] >= 0.0

    def test_create_instant_display_response(self):
        """Test the instant display response creation"""
        response_segments = ["Part 1", "Part 2", "Part 3"]
        result = create_instant_display_response(response_segments)

        assert result["reading_time"] == 0.0
        assert result["min_reading_delay"] == 0.0
        assert len(result["response_segments"]) == 3

        for segment in result["response_segments"]:
            assert segment["writing_delay"] == 0.0
            assert segment["inter_segment_delay"] == 0.0

    def test_response_segments_structure(self):
        """Test that response segments have correct structure"""
        message = "Test message"
        response_segments = ["First part", "Second part"]

        result = calculate_typing_delays(
            message, response_segments, self.bot_config)

        # Check structure
        assert "reading_time" in result
        assert "min_reading_delay" in result
        assert "response_segments" in result

        # Check response segments structure
        for segment in result["response_segments"]:
            assert "content" in segment
            assert "writing_delay" in segment
            assert "inter_segment_delay" in segment

            # Content should match original
            assert segment["content"] in response_segments

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

        assert result["reading_time"] >= expected_min_reading
        assert result["reading_time"] <= expected_max_reading

        # Writing delay should be reasonable (based on response length)
        segment = result["response_segments"][0]
        response_words = len(segment["content"].split())
        expected_min_writing = (response_words * 60 / 200) + 0.05 + 0.1
        expected_max_writing = (response_words * 60 / 200) + 0.15 + 0.3

        assert segment["writing_delay"] >= expected_min_writing
        assert segment["writing_delay"] <= expected_max_writing

        # Inter-segment delay should be within range
        assert segment["inter_segment_delay"] >= 0.1
        assert segment["inter_segment_delay"] <= 0.3

    def test_empty_response_segments(self):
        """Test handling of empty response segments"""
        message = "Test"
        response_segments = []

        result = calculate_typing_delays(
            message, response_segments, self.bot_config)

        assert len(result["response_segments"]) == 0
        # Reading time should still be calculated
        assert result["reading_time"] > 0.0

    def test_single_response_segment(self):
        """Test handling of single response segment"""
        message = "Test message"
        response_segments = ["Single response"]

        result = calculate_typing_delays(
            message, response_segments, self.bot_config)

        assert len(result["response_segments"]) == 1
        segment = result["response_segments"][0]
        assert segment["content"] == "Single response"
        assert segment["writing_delay"] > 0.0
        assert segment["inter_segment_delay"] >= 0.0


if __name__ == "__main__":
    unittest.main()
