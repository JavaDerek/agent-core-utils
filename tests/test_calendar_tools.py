"""Comprehensive tests for calendar_tools module."""

import pytest
from datetime import date
from unittest.mock import patch

import calendar_tools


class TestWordToInt:
    """Tests for _word_to_int function."""
    
    def test_digit_string(self):
        """Test conversion of digit strings to integers."""
        assert calendar_tools._word_to_int("5") == 5
        assert calendar_tools._word_to_int("123") == 123
        assert calendar_tools._word_to_int("0") == 0
    
    def test_word_to_number(self):
        """Test conversion of word strings to integers."""
        assert calendar_tools._word_to_int("one") == 1
        assert calendar_tools._word_to_int("five") == 5
        assert calendar_tools._word_to_int("twelve") == 12
    
    def test_case_insensitive(self):
        """Test that word conversion is case insensitive."""
        assert calendar_tools._word_to_int("ONE") == 1
        assert calendar_tools._word_to_int("Five") == 5
        assert calendar_tools._word_to_int("TWELVE") == 12
    
    def test_invalid_word(self):
        """Test handling of invalid words."""
        assert calendar_tools._word_to_int("invalid") is None
        assert calendar_tools._word_to_int("thirteen") is None
        assert calendar_tools._word_to_int("") is None
    
    def test_mixed_input(self):
        """Test handling of mixed valid/invalid inputs."""
        assert calendar_tools._word_to_int("zero") == 0
        assert calendar_tools._word_to_int("ten") == 10
        assert calendar_tools._word_to_int("not_a_number") is None


class TestGetCurrentDate:
    """Tests for get_current_date function."""
    
    def test_returns_date_object(self):
        """Test that function returns a date object."""
        result = calendar_tools.get_current_date()
        assert isinstance(result, date)
    
    @patch('calendar_tools.date')
    def test_calls_date_today(self, mock_date):
        """Test that function calls date.today()."""
        mock_date.today.return_value = date(2023, 6, 15)
        result = calendar_tools.get_current_date()
        mock_date.today.assert_called_once()
        assert result == date(2023, 6, 15)


class TestParseRelativeDate:
    """Tests for parse_relative_date function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_date = date(2023, 6, 15)  # June 15, 2023 (Thursday)
    
    def test_next_month(self):
        """Test parsing 'next month' expressions."""
        result = calendar_tools.parse_relative_date("next july", base=self.base_date)
        assert result == date(2023, 7, 1)  # Next July in same year
        
        result = calendar_tools.parse_relative_date("next january", base=self.base_date)
        assert result == date(2024, 1, 1)  # Next January in next year
    
    def test_last_month(self):
        """Test parsing 'last month' expressions."""
        result = calendar_tools.parse_relative_date("last may", base=self.base_date)
        assert result == date(2023, 5, 1)  # Last May in same year
        
        result = calendar_tools.parse_relative_date("last july", base=self.base_date)
        assert result == date(2022, 7, 1)  # Last July in previous year
    
    def test_in_future_with_digits(self):
        """Test parsing 'in X units' expressions with digits."""
        result = calendar_tools.parse_relative_date("in 5 days", base=self.base_date)
        assert result == date(2023, 6, 20)
        
        result = calendar_tools.parse_relative_date("in 2 weeks", base=self.base_date)
        assert result == date(2023, 6, 29)
        
        result = calendar_tools.parse_relative_date("in 3 months", base=self.base_date)
        assert result == date(2023, 9, 15)
        
        result = calendar_tools.parse_relative_date("in 1 year", base=self.base_date)
        assert result == date(2024, 6, 15)
    
    def test_in_future_with_words(self):
        """Test parsing 'in X units' expressions with words."""
        result = calendar_tools.parse_relative_date("in five days", base=self.base_date)
        assert result == date(2023, 6, 20)
        
        result = calendar_tools.parse_relative_date("in two weeks", base=self.base_date)
        assert result == date(2023, 6, 29)
    
    def test_from_now_expressions(self):
        """Test parsing 'X units from now' expressions."""
        result = calendar_tools.parse_relative_date("5 days from now", base=self.base_date)
        assert result == date(2023, 6, 20)
        
        result = calendar_tools.parse_relative_date("two weeks from now", base=self.base_date)
        assert result == date(2023, 6, 29)
    
    def test_ago_expressions(self):
        """Test parsing 'X units ago' expressions."""
        result = calendar_tools.parse_relative_date("5 days ago", base=self.base_date)
        assert result == date(2023, 6, 10)
        
        result = calendar_tools.parse_relative_date("two weeks ago", base=self.base_date)
        assert result == date(2023, 6, 1)
        
        result = calendar_tools.parse_relative_date("1 month ago", base=self.base_date)
        assert result == date(2023, 5, 15)
    
    def test_singular_and_plural_units(self):
        """Test that both singular and plural units work."""
        result1 = calendar_tools.parse_relative_date("1 day ago", base=self.base_date)
        result2 = calendar_tools.parse_relative_date("1 days ago", base=self.base_date)
        assert result1 == result2 == date(2023, 6, 14)
    
    def test_case_insensitive(self):
        """Test that parsing is case insensitive."""
        result1 = calendar_tools.parse_relative_date("NEXT JULY", base=self.base_date)
        result2 = calendar_tools.parse_relative_date("next july", base=self.base_date)
        assert result1 == result2 == date(2023, 7, 1)
    
    def test_invalid_expressions(self):
        """Test handling of invalid expressions."""
        assert calendar_tools.parse_relative_date("invalid expression", base=self.base_date) is None
        assert calendar_tools.parse_relative_date("", base=self.base_date) is None
        assert calendar_tools.parse_relative_date("next invalid_month", base=self.base_date) is None
    
    def test_edge_case_invalid_numbers(self):
        """Test edge cases with invalid number words."""
        # Invalid word numbers should return None
        assert calendar_tools.parse_relative_date("thirteen days ago", base=self.base_date) is None
        assert calendar_tools.parse_relative_date("invalid_number days ago", base=self.base_date) is None
    
    def test_default_base_date(self):
        """Test that default base date is used when not provided."""
        with patch('calendar_tools.get_current_date') as mock_get_current_date:
            mock_get_current_date.return_value = date(2023, 6, 15)
            result = calendar_tools.parse_relative_date("5 days ago")
            assert result == date(2023, 6, 10)
            mock_get_current_date.assert_called_once()
    
    def test_boundary_month_transitions(self):
        """Test month boundary transitions."""
        # Test from December to January
        base = date(2023, 12, 15)
        result = calendar_tools.parse_relative_date("next january", base=base)
        assert result == date(2024, 1, 1)
        
        # Test from January to December (previous year)
        base = date(2023, 1, 15)
        result = calendar_tools.parse_relative_date("last december", base=base)
        assert result == date(2022, 12, 1)


class TestResolveLativeDates:
    """Tests for resolve_relative_dates function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_date = date(2023, 6, 15)
    
    def test_single_relative_date(self):
        """Test resolving single relative date in text."""
        text = "The meeting is next july."
        result = calendar_tools.resolve_relative_dates(text, base=self.base_date)
        assert result == "The meeting is 2023-07-01."
    
    def test_multiple_relative_dates(self):
        """Test resolving multiple relative dates in text."""
        text = "From 5 days ago to next july, we had good weather."
        result = calendar_tools.resolve_relative_dates(text, base=self.base_date)
        assert result == "From 2023-06-10 to 2023-07-01, we had good weather."
    
    def test_case_insensitive_matching(self):
        """Test case insensitive pattern matching."""
        text = "The event is NEXT JULY and 5 DAYS AGO we planned it."
        result = calendar_tools.resolve_relative_dates(text, base=self.base_date)
        assert result == "The event is 2023-07-01 and 2023-06-10 we planned it."
    
    def test_no_relative_dates(self):
        """Test text with no relative dates."""
        text = "This is just regular text with no dates."
        result = calendar_tools.resolve_relative_dates(text, base=self.base_date)
        assert result == text
    
    def test_invalid_relative_dates_unchanged(self):
        """Test that invalid relative dates are left unchanged."""
        text = "Meeting is next invalid_month and some random text."
        result = calendar_tools.resolve_relative_dates(text, base=self.base_date)
        assert result == text  # Should be unchanged
    
    def test_mixed_valid_invalid_dates(self):
        """Test text with both valid and invalid relative dates."""
        text = "From next july to invalid_expression and 5 days ago."
        result = calendar_tools.resolve_relative_dates(text, base=self.base_date)
        assert result == "From 2023-07-01 to invalid_expression and 2023-06-10."
    
    def test_default_base_date(self):
        """Test that default base date is used when not provided."""
        with patch('calendar_tools.get_current_date') as mock_get_current_date:
            mock_get_current_date.return_value = date(2023, 6, 15)
            text = "Meeting is 5 days ago."
            result = calendar_tools.resolve_relative_dates(text)
            assert result == "Meeting is 2023-06-10."
            mock_get_current_date.assert_called_once()
    
    def test_all_supported_patterns(self):
        """Test all supported regex patterns."""
        patterns_and_expected = [
            ("next july", "2023-07-01"),
            ("last may", "2023-05-01"),
            ("5 days from now", "2023-06-20"),
            ("two weeks ago", "2023-06-01"),
            ("in 3 months", "2023-09-15"),
        ]
        
        for pattern, expected in patterns_and_expected:
            text = f"The date is {pattern}."
            result = calendar_tools.resolve_relative_dates(text, base=self.base_date)
            assert result == f"The date is {expected}."
    
    def test_repeated_phrases(self):
        """Test handling of repeated relative date phrases."""
        text = "next july and next july again"
        result = calendar_tools.resolve_relative_dates(text, base=self.base_date)
        assert result == "2023-07-01 and 2023-07-01 again"


# Parameterized test scenarios
@pytest.mark.parametrize("word,expected", [
    ("0", 0),
    ("5", 5),
    ("123", 123),
    ("zero", 0),
    ("one", 1),
    ("twelve", 12),
    ("ONE", 1),
    ("Five", 5),
    ("invalid", None),
    ("thirteen", None),
    ("", None),
])
def test_word_to_int_parameterized(word, expected):
    """Parameterized tests for _word_to_int function."""
    assert calendar_tools._word_to_int(word) == expected


@pytest.mark.parametrize("expression,base_date,expected_date", [
    ("next july", date(2023, 6, 15), date(2023, 7, 1)),
    ("next january", date(2023, 6, 15), date(2024, 1, 1)),
    ("next march", date(2023, 6, 15), date(2024, 3, 1)),
    ("last may", date(2023, 6, 15), date(2023, 5, 1)),
    ("last july", date(2023, 6, 15), date(2022, 7, 1)),
    ("last april", date(2023, 6, 15), date(2023, 4, 1)),
    ("5 days ago", date(2023, 6, 15), date(2023, 6, 10)),
    ("two weeks from now", date(2023, 6, 15), date(2023, 6, 29)),
    ("in 1 month", date(2023, 6, 15), date(2023, 7, 15)),
    ("3 years ago", date(2023, 6, 15), date(2020, 6, 15)),
])
def test_parse_relative_date_parameterized(expression, base_date, expected_date):
    """Parameterized tests for parse_relative_date function."""
    result = calendar_tools.parse_relative_date(expression, base=base_date)
    assert result == expected_date


@pytest.mark.parametrize("expression,base_date", [
    ("invalid expression", date(2023, 6, 15)),
    ("next invalid_month", date(2023, 6, 15)),
    ("thirteen days ago", date(2023, 6, 15)),
    ("", date(2023, 6, 15)),
])
def test_parse_relative_date_invalid_parameterized(expression, base_date):
    """Parameterized tests for invalid expressions in parse_relative_date."""
    result = calendar_tools.parse_relative_date(expression, base=base_date)
    assert result is None