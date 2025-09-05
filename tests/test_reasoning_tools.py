"""Tests for agent_core_utils.reasoning_tools module."""

import json
from unittest.mock import Mock, patch
import pytest
from agent_core_utils.reasoning_tools import (
    analyze_text_with_llm,
    analyze_html_with_llm,
    extract_structured_data_with_llm,
)


class TestAnalyzeTextWithLLM:
    """Tests for analyze_text_with_llm function."""

    def test_analyze_text_with_llm_success(self):
        """Test successful text analysis with LLM."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = '{"result": "success"}'
        mock_client.invoke.return_value = mock_response
        
        result = analyze_text_with_llm(
            mock_client, 
            "sample text", 
            "Analyze this: {description}"
        )
        
        assert result == '{"result": "success"}'
        mock_client.invoke.assert_called_once()
        call_args = mock_client.invoke.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0].content == "Analyze this: sample text"

    def test_analyze_text_with_llm_json_code_fences(self):
        """Test handling of JSON wrapped in markdown code fences."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = '```json\n{"result": "success"}\n```'
        mock_client.invoke.return_value = mock_response
        
        result = analyze_text_with_llm(
            mock_client, 
            "sample text", 
            "Analyze this: {description}"
        )
        
        assert result == '{"result": "success"}'

    def test_analyze_text_with_llm_generic_code_fences(self):
        """Test handling of content wrapped in generic code fences."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = '```\n{"result": "success"}\n```'
        mock_client.invoke.return_value = mock_response
        
        result = analyze_text_with_llm(
            mock_client, 
            "sample text", 
            "Analyze this: {description}"
        )
        
        assert result == '{"result": "success"}'

    def test_analyze_text_with_llm_list_content(self):
        """Test handling of LLM response that returns a list."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = ["part1", "part2", "part3"]
        mock_client.invoke.return_value = mock_response
        
        result = analyze_text_with_llm(
            mock_client, 
            "sample text", 
            "Analyze this: {description}"
        )
        
        assert result == "part1\npart2\npart3"

    def test_analyze_text_with_llm_non_string_content(self):
        """Test handling of LLM response that returns non-string content."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = {"key": "value"}
        mock_client.invoke.return_value = mock_response
        
        result = analyze_text_with_llm(
            mock_client, 
            "sample text", 
            "Analyze this: {description}"
        )
        
        assert result == "{'key': 'value'}"

    def test_analyze_text_with_llm_exception_handling(self):
        """Test exception handling in text analysis."""
        mock_client = Mock()
        mock_client.invoke.side_effect = Exception("LLM error")
        
        result = analyze_text_with_llm(
            mock_client, 
            "sample text", 
            "Analyze this: {description}"
        )
        
        parsed_result = json.loads(result)
        assert "error" in parsed_result
        assert "LLM error" in parsed_result["error"]


class TestAnalyzeHtmlWithLLM:
    """Tests for analyze_html_with_llm function."""

    def test_analyze_html_with_llm(self):
        """Test HTML analysis delegates to text analysis."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = "html analysis result"
        mock_client.invoke.return_value = mock_response
        
        result = analyze_html_with_llm(
            mock_client,
            "<html><body>test</body></html>",
            "Analyze this HTML: {description}"
        )
        
        assert result == "html analysis result"
        mock_client.invoke.assert_called_once()


class TestExtractStructuredDataWithLLM:
    """Tests for extract_structured_data_with_llm function."""

    def test_extract_structured_data_success(self):
        """Test successful structured data extraction."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = '{"name": "test", "value": 42}'
        mock_client.invoke.return_value = mock_response
        
        result = extract_structured_data_with_llm(
            mock_client,
            "sample text",
            "Extract data from: {description}"
        )
        
        assert result == {"name": "test", "value": 42}

    def test_extract_structured_data_with_model_validation(self):
        """Test structured data extraction with Pydantic model validation."""
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
            value: int
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = '{"name": "test", "value": 42}'
        mock_client.invoke.return_value = mock_response
        
        result = extract_structured_data_with_llm(
            mock_client,
            "sample text",
            "Extract data from: {description}",
            TestModel
        )
        
        assert result == {"name": "test", "value": 42}

    def test_extract_structured_data_json_parse_error(self):
        """Test handling of JSON parsing errors."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = "invalid json"
        mock_client.invoke.return_value = mock_response
        
        result = extract_structured_data_with_llm(
            mock_client,
            "sample text",
            "Extract data from: {description}"
        )
        
        assert "error" in result
        assert "JSON parsing failed" in result["error"]

    def test_extract_structured_data_validation_error(self):
        """Test handling of Pydantic validation errors."""
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
            value: int
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = '{"name": "test", "value": "not_an_int"}'
        mock_client.invoke.return_value = mock_response
        
        result = extract_structured_data_with_llm(
            mock_client,
            "sample text",
            "Extract data from: {description}",
            TestModel
        )
        
        assert "error" in result
        assert "Validation failed" in result["error"]
