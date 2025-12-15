"""
Transcript to String Converter

Utility to convert transcript JSON to a single comma-separated string.
Can be used as a module or run as a standalone script.
"""
import json
from typing import List, Dict, Any


def convert_transcript_to_string(transcript: List[Dict[str, Any]]) -> str:
    # Flatten the data into a list of strings
    flat_list = [str(value) for item in transcript for value in (item['word'], item['start_ms'], item['end_ms'])]

    # Join the list into a single string
    return ", ".join(flat_list)