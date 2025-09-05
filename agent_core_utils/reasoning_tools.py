"""Generic LLM-based reasoning utilities for agent applications."""

import json
import logging
import re

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def analyze_text_with_llm(
    llm_client: ChatOpenAI, text_to_analyze: str, question: str
) -> str:
    """
    Analyze a block of text using a pre-initialized LLM client.
    
    Handles cases where the LLM wraps JSON responses in markdown code fences.
    
    Args:
        llm_client: Pre-initialized ChatOpenAI client
        text_to_analyze: The text content to analyze
        question: The prompt/question to ask about the text (can include {description} placeholder)
        
    Returns:
        String response from the LLM, with code fences stripped if present
    """
    logger.info("REASONING_TOOL: Analyzing descriptive text...")
    
    # Format the question with the text to analyze
    formatted_question = question.format(description=text_to_analyze)
    messages = [HumanMessage(content=formatted_question)]
    
    try:
        response = llm_client.invoke(messages)
        content = response.content
        
        # Handle different content types from LLM response
        if isinstance(content, list):
            # Some LLM responses return lists, join them
            content = "\n".join(str(item) for item in content)
        elif not isinstance(content, str):
            content = str(content)

        # Handle JSON wrapped in markdown code fences
        # Use regex to capture JSON regardless of newline placement or line endings
        match = re.search(r"```json\s*\r?\n?(.*?)```", content, re.DOTALL)
        if not match:
            # Try generic code fences
            match = re.search(r"```\s*\r?\n?(.*?)```", content, re.DOTALL)
        
        json_str = match.group(1) if match else content

        logger.info("REASONING_TOOL: Text analysis successful.")
        return json_str.strip()

    except Exception as e:
        error_msg = f"An error occurred during text analysis LLM call: {e}"
        logger.error("REASONING_TOOL: %s", error_msg)
        return json.dumps({"error": error_msg})


def analyze_html_with_llm(llm_client: ChatOpenAI, html_text: str, prompt: str) -> str:
    """
    Analyze raw HTML content using the LLM.
    
    Args:
        llm_client: Pre-initialized ChatOpenAI client
        html_text: Raw HTML content to analyze
        prompt: The analysis prompt to use
        
    Returns:
        String response from the LLM analysis
    """
    return analyze_text_with_llm(llm_client, html_text, prompt)


def extract_structured_data_with_llm(
    llm_client: ChatOpenAI, text: str, prompt: str, model_class=None
) -> dict:
    """
    Extract structured data from text using LLM and optionally validate with a Pydantic model.
    
    Args:
        llm_client: Pre-initialized ChatOpenAI client
        text: Text to extract data from
        prompt: Extraction prompt
        model_class: Optional Pydantic model class for validation
        
    Returns:
        Dictionary with extracted data, or error dict if parsing fails
    """
    json_str = analyze_text_with_llm(llm_client, text, prompt)
    
    try:
        data = json.loads(json_str)
        
        # Validate with Pydantic model if provided
        if model_class:
            try:
                validated = model_class.model_validate(data)
                return validated.model_dump()
            except Exception as e:
                logger.error("Failed to validate extracted data: %s", e)
                return {"error": f"Validation failed: {e}"}
        
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse LLM response as JSON: %s", e)
        return {"error": f"JSON parsing failed: {e}"}
