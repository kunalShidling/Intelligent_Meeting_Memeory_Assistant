"""
Text Summarization Module using Groq API

This module provides functionality to summarize transcribed text into bullet points
using Groq's powerful language models.

Author: Audio Transcription System
Date: 2026
"""

import os
import re
from typing import Optional, List, Tuple
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TextSummarizer:
    """
    A class for summarizing text using Groq API.
    
    Attributes:
        api_key (str): Groq API key
        model (str): The model to use for summarization
        client: The Groq client instance
    """
    
    AVAILABLE_MODELS = [
        'llama-3.3-70b-versatile',
        'llama-3.1-70b-versatile',
        'llama-3.1-8b-instant',
        'mixtral-8x7b-32768',
        'gemma2-9b-it'
    ]

    SUMMARY_SECTION_TITLE = "Meeting Summary"
    ACTION_SECTION_TITLE = "Action Items"
    DEFAULT_SUMMARY_BULLETS = 5
    DEFAULT_ACTION_BULLETS = 5
    MAX_BULLET_CHARS = 140
    
    def __init__(self, api_key: Optional[str] = None, model: str = 'llama-3.3-70b-versatile'):
        """
        Initialize the TextSummarizer with Groq API.
        
        Args:
            api_key (str, optional): Groq API key. If not provided, reads from GROQ_API_KEY env variable
            model (str): Model to use for summarization. Defaults to 'llama-3.3-70b-versatile'
        
        Raises:
            ValueError: If API key is not provided and not found in environment
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Groq API key not found. Please provide it as an argument or set GROQ_API_KEY environment variable.\n"
                "Get your API key from: https://console.groq.com/keys"
            )
        
        if model not in self.AVAILABLE_MODELS:
            print(f"Warning: Model '{model}' not in standard list. Using anyway...")
        
        self.model = model
        self.client = Groq(api_key=self.api_key)
        print(f"Groq API initialized with model: {model}")
    
    def summarize_to_bullets(
        self,
        text: str,
        max_bullets: int = 10,
        focus: Optional[str] = None,
        verbose: bool = False
    ) -> str:
        """
        Summarize text into concise bullet points.
        
        Args:
            text (str): The text to summarize
            max_bullets (int): Maximum number of bullet points. Defaults to 10
            focus (str, optional): Specific focus area for summarization (e.g., "action items", "key decisions")
            verbose (bool): Print progress information
        
        Returns:
            str: Summarized text in bullet point format
        
        Raises:
            Exception: If API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        if verbose:
            print(f"Summarizing text ({len(text)} characters)...")
        
        # Construct the prompt
        focus_instruction = f" Focus on: {focus}." if focus else ""
        
        prompt = f"""Analyze the following conversation/text and create a short, scannable summary in bullet points.

Requirements:
- Create up to {max_bullets} bullet points
    - Each bullet should be clear, self-contained, and short (<= {self.MAX_BULLET_CHARS} characters)
    - Focus on key decisions, action items, and important discussion topics
    - Remove filler words and repeated content
    - Ignore small talk or tangents
    - Use professional, easy-to-understand language
    - Start each bullet with a bullet point symbol (•){focus_instruction}

Text to summarize:
{text}

Provide ONLY the bullet points, no additional commentary."""
        
        try:
            # Call Groq API
            if verbose:
                print(f"Calling Groq API with model: {self.model}")
            
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at distilling conversations into short, actionable bullet points. Focus on decisions, action items, and key topics only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3,  # Lower temperature for more focused summaries
                max_tokens=700,
                top_p=1,
                stream=False
            )
            
            summary = chat_completion.choices[0].message.content.strip()
            bullets = self._extract_bullets(summary)
            if not bullets:
                bullets = self._fallback_bullets(summary, max_bullets)
            bullets = self._compress_bullets(bullets, max_bullets, self.MAX_BULLET_CHARS)
            summary = "\n".join([f"• {bullet}" for bullet in bullets])
            
            if verbose:
                print(f"Summary generated successfully ({len(summary)} characters)")
            
            return summary
        
        except Exception as e:
            raise Exception(f"Failed to generate summary: {str(e)}")

    def summarize_meeting(
        self,
        text: str,
        max_summary_bullets: int = DEFAULT_SUMMARY_BULLETS,
        max_action_items: int = DEFAULT_ACTION_BULLETS,
        verbose: bool = False
    ) -> str:
        """
        Create a structured, concise meeting summary with action items.

        Args:
            text (str): The text to summarize
            max_summary_bullets (int): Maximum summary bullets
            max_action_items (int): Maximum action items
            verbose (bool): Print progress information

        Returns:
            str: Meeting Summary + Action Items sections
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if verbose:
            print(f"Summarizing meeting text ({len(text)} characters)...")

        prompt = f"""Summarize the following meeting transcript.

Output format (exactly):
{self.SUMMARY_SECTION_TITLE}:
• bullet 1
• bullet 2

{self.ACTION_SECTION_TITLE}:
• Name → task (if owner known)

Rules:
- Keep it short and scannable
- Use up to {max_summary_bullets} bullets in {self.SUMMARY_SECTION_TITLE}
- Use up to {max_action_items} bullets in {self.ACTION_SECTION_TITLE}
- Ignore small talk and filler
- Avoid repetition
- Each bullet <= {self.MAX_BULLET_CHARS} characters
- If there are no action items, write "• None" under {self.ACTION_SECTION_TITLE}

Transcript:
"""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You create short, professional meeting summaries with clear action items."
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n{text}"
                    }
                ],
                model=self.model,
                temperature=0.2,
                max_tokens=700,
                top_p=1,
                stream=False
            )

            raw_summary = chat_completion.choices[0].message.content.strip()
            summary_bullets, action_bullets = self._split_sections(raw_summary)

            if not summary_bullets:
                summary_bullets = self._fallback_bullets(raw_summary, max_summary_bullets)

            summary_bullets = self._compress_bullets(
                summary_bullets,
                max_summary_bullets,
                self.MAX_BULLET_CHARS
            )
            action_bullets = self._compress_bullets(
                action_bullets,
                max_action_items,
                self.MAX_BULLET_CHARS
            )

            return self._format_sections(summary_bullets, action_bullets)

        except Exception as e:
            raise Exception(f"Failed to generate meeting summary: {str(e)}")

    def _extract_bullets(self, text: str) -> List[str]:
        bullets = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if re.match(r"^[\-•*]\s+", line):
                bullets.append(line)
        return bullets

    def _fallback_bullets(self, text: str, max_bullets: int) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        bullets = [s.strip() for s in sentences if s.strip()]
        return bullets[:max_bullets]

    def _clean_bullet(self, bullet: str) -> str:
        bullet = re.sub(r"^[\-•*]\s+", "", bullet).strip()
        bullet = re.sub(r"\s+", " ", bullet)
        return bullet.strip(" .;:")

    def _truncate_bullet(self, bullet: str, max_chars: int) -> str:
        if len(bullet) <= max_chars:
            return bullet
        truncated = bullet[:max_chars].rsplit(" ", 1)[0]
        return truncated + "..."

    def _compress_bullets(self, bullets: List[str], max_bullets: int, max_chars: int) -> List[str]:
        cleaned = []
        seen = set()
        for bullet in bullets:
            text = self._clean_bullet(bullet)
            if not text:
                continue
            key = re.sub(r"[^a-z0-9]+", "", text.lower())
            if not key or key in seen:
                continue
            seen.add(key)
            cleaned.append(self._truncate_bullet(text, max_chars))
            if len(cleaned) >= max_bullets:
                break
        return cleaned

    def _split_sections(self, text: str) -> Tuple[List[str], List[str]]:
        summary_bullets = []
        action_bullets = []
        current = None

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if lower.startswith(self.SUMMARY_SECTION_TITLE.lower()):
                current = "summary"
                continue
            if lower.startswith(self.ACTION_SECTION_TITLE.lower()):
                current = "action"
                continue
            if re.match(r"^[\-•*]\s+", stripped):
                if current == "action":
                    action_bullets.append(stripped)
                else:
                    summary_bullets.append(stripped)

        return summary_bullets, action_bullets

    def _format_sections(self, summary_bullets: List[str], action_bullets: List[str]) -> str:
        lines = [f"{self.SUMMARY_SECTION_TITLE}:"]
        for bullet in summary_bullets:
            lines.append(f"• {bullet}")

        lines.append("")
        lines.append(f"{self.ACTION_SECTION_TITLE}:")
        if action_bullets:
            for bullet in action_bullets:
                lines.append(f"• {bullet}")
        else:
            lines.append("• None")

        return "\n".join(lines).strip()
    
    def summarize_with_structure(
        self,
        text: str,
        verbose: bool = False
    ) -> dict:
        """
        Create a structured summary with multiple sections.
        
        Args:
            text (str): The text to summarize
            verbose (bool): Print progress information
        
        Returns:
            dict: Dictionary with structured summary sections
        """
        if verbose:
            print(f"Creating structured summary...")
        
        prompt = f"""Analyze the following conversation/text and create a structured summary with the following sections:

1. MAIN TOPICS: Key subjects discussed (2-4 bullet points)
2. KEY POINTS: Important details or facts (3-5 bullet points)
3. ACTION ITEMS: Tasks or next steps mentioned, if any (bullet points)
4. DECISIONS: Any decisions made or conclusions reached (bullet points)

Text to analyze:
{text}

Format your response EXACTLY as:
MAIN TOPICS:
• [topic 1]
• [topic 2]

KEY POINTS:
• [point 1]
• [point 2]

ACTION ITEMS:
• [item 1] (or write "None" if no action items)

DECISIONS:
• [decision 1] (or write "None" if no decisions)"""
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing conversations and creating structured summaries."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=1500,
                top_p=1,
                stream=False
            )
            
            summary_text = chat_completion.choices[0].message.content.strip()
            
            # Parse the structured response
            sections = {
                'raw': summary_text,
                'main_topics': [],
                'key_points': [],
                'action_items': [],
                'decisions': []
            }
            
            current_section = None
            for line in summary_text.split('\n'):
                line = line.strip()
                if 'MAIN TOPICS:' in line:
                    current_section = 'main_topics'
                elif 'KEY POINTS:' in line:
                    current_section = 'key_points'
                elif 'ACTION ITEMS:' in line:
                    current_section = 'action_items'
                elif 'DECISIONS:' in line:
                    current_section = 'decisions'
                elif line.startswith('•') and current_section:
                    sections[current_section].append(line)
            
            if verbose:
                print("Structured summary generated successfully")
            
            return sections
        
        except Exception as e:
            raise Exception(f"Failed to generate structured summary: {str(e)}")


def main():
    """Example usage of the TextSummarizer."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Summarize text using Groq API')
    parser.add_argument('text_file', help='Path to text file to summarize')
    parser.add_argument('--api-key', help='Groq API key (or set GROQ_API_KEY env variable)')
    parser.add_argument('--model', default='llama-3.3-70b-versatile', help='Model to use')
    parser.add_argument('--bullets', type=int, default=10, help='Max number of bullet points')
    parser.add_argument('--structured', action='store_true', help='Use structured summary format')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Read text file
    try:
        with open(args.text_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Initialize summarizer
    try:
        summarizer = TextSummarizer(api_key=args.api_key, model=args.model)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Generate summary
    try:
        if args.structured:
            result = summarizer.summarize_with_structure(text, verbose=args.verbose)
            print("\n" + "="*70)
            print("STRUCTURED SUMMARY")
            print("="*70)
            print(result['raw'])
            print("="*70)
        else:
            summary = summarizer.summarize_to_bullets(
                text,
                max_bullets=args.bullets,
                verbose=args.verbose
            )
            print("\n" + "="*70)
            print("SUMMARY")
            print("="*70)
            print(summary)
            print("="*70)
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
