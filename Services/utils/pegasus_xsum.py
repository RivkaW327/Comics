import re
import json
import time
import random
from typing import List, Optional
from datetime import datetime, timedelta
from FastAPIProject.config.config_loader import config
from FastAPIProject.Models.domain.entity import Entity
from google import genai


class GeminiQuotaManager:
    """Manages Gemini API quota to stay within free tier limits"""

    def __init__(self):
        # Free tier limits (conservative estimates)
        self.max_requests_per_minute = 10  # Conservative (actual limit is 15)
        self.max_requests_per_day = 1200  # Conservative (actual limit is 1500)
        self.max_tokens_per_minute = 25000  # Conservative (actual limit is 32000)

        # Tracking
        self.requests_this_minute = []
        self.requests_today = 0
        self.tokens_this_minute = []
        self.last_reset_day = datetime.now().date()

    def can_make_request(self, estimated_tokens: int = 1000) -> tuple[bool, Optional[float]]:
        """Check if we can make a request and return wait time if needed"""
        now = datetime.now()

        # Reset daily counter
        if now.date() > self.last_reset_day:
            self.requests_today = 0
            self.last_reset_day = now.date()

        # Clean old requests (older than 1 minute)
        minute_ago = now - timedelta(minutes=1)
        self.requests_this_minute = [req_time for req_time in self.requests_this_minute if req_time > minute_ago]
        self.tokens_this_minute = [(time, tokens) for time, tokens in self.tokens_this_minute if time > minute_ago]

        # Check daily limit
        if self.requests_today >= self.max_requests_per_day:
            return False, None  # Need to wait until tomorrow

        # Check per-minute request limit
        if len(self.requests_this_minute) >= self.max_requests_per_minute:
            oldest_request = min(self.requests_this_minute)
            wait_time = 60 - (now - oldest_request).total_seconds()
            return False, max(wait_time, 1)

        # Check per-minute token limit
        current_tokens = sum(tokens for _, tokens in self.tokens_this_minute)
        if current_tokens + estimated_tokens > self.max_tokens_per_minute:
            if self.tokens_this_minute:
                oldest_token_time = min(time for time, _ in self.tokens_this_minute)
                wait_time = 60 - (now - oldest_token_time).total_seconds()
                return False, max(wait_time, 1)

        return True, 0

    def record_request(self, tokens_used: int = 1000):
        """Record a successful request"""
        now = datetime.now()
        self.requests_this_minute.append(now)
        self.tokens_this_minute.append((now, tokens_used))
        self.requests_today += 1


# Global quota manager instance
quota_manager = GeminiQuotaManager()


def estimate_tokens(text: str) -> int:
    """Rough estimation of tokens (1 token ≈ 4 characters for English)"""
    return len(text) // 4


def abstractive_summarization(paragraps_txt: List[str]) -> List[str]:
    """Quota-aware summarization with intelligent batching"""

    # For free tier, process smaller batches
    if len(paragraps_txt) > 8:
        print(f"Large request ({len(paragraps_txt)} paragraphs) - processing in smaller batches for quota management")
        return process_in_small_batches(paragraps_txt, batch_size=5)

    # Estimate tokens for this request
    text_content = str(paragraps_txt)
    estimated_tokens = estimate_tokens(text_content) * 2  # Multiply by 2 for input + output

    # Check quota before making request
    can_request, wait_time = quota_manager.can_make_request(estimated_tokens)

    if not can_request:
        if wait_time is None:
            print("Daily quota exceeded. Please try again tomorrow.")
            return []
        else:
            print(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time + 1)  # Add 1 second buffer

    return abstractive_summarization_with_quota(paragraps_txt, estimated_tokens)


def abstractive_summarization_with_quota(paragraps_txt: List[str], estimated_tokens: int) -> List[str]:
    """Summarization with quota tracking"""

    # Create numbered list of paragraphs for better tracking
    numbered_paragraphs = [f"Paragraph {i + 1}: {para}" for i, para in enumerate(paragraps_txt)]

    # Shorter, more efficient prompt for free tier
    prompt = f"""
Create exactly {len(paragraps_txt)} brief summaries, one for each paragraph.
Return ONLY a valid JSON array format: ["summary1", "summary2", ...]

Paragraphs to summarize:
{chr(10).join(numbered_paragraphs)}

Remember: Return exactly {len(paragraps_txt)} summaries in JSON array format.
"""

    try:
        client = genai.Client(api_key=config["services"]["google_gemini"]["api_key"])

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[prompt],
        )

        # Record successful request
        quota_manager.record_request(estimated_tokens)

        summ = response.candidates[0].content.parts[0].text.strip()
        print(f"Raw response: {summ}")

        if not summ:
            print("Empty response from Gemini")
            return []

        parsed_list = parse_gemini_list_response(summ, expected_count=len(paragraps_txt))
        print(f"Successfully processed {len(parsed_list)} summaries (expected {len(paragraps_txt)})")

        # If we got fewer summaries than expected, pad with placeholders
        if len(parsed_list) < len(paragraps_txt):
            print(f"Warning: Got {len(parsed_list)} summaries but expected {len(paragraps_txt)}")
            while len(parsed_list) < len(paragraps_txt):
                parsed_list.append(f"[Summary unavailable for paragraph {len(parsed_list) + 1}]")

        return parsed_list

    except Exception as e:
        error_str = str(e)

        if "429" in error_str or "quota" in error_str.lower():
            print("Quota exceeded - implementing longer delay")
            # Extract retry delay if provided
            if "retryDelay" in error_str:
                import re
                delay_match = re.search(r"'retryDelay': '(\d+)s'", error_str)
                if delay_match:
                    delay = int(delay_match.group(1))
                    print(f"Waiting {delay} seconds as suggested by API")
                    time.sleep(delay + 2)  # Add buffer
            else:
                time.sleep(60)  # Default 1 minute wait

            return []

        print(f"Other error: {e}")
        return []


def process_in_small_batches(paragraps_txt: List[str], batch_size: int = 5) -> List[str]:
    """Process in very small batches for quota management"""
    all_summaries = []

    for i in range(0, len(paragraps_txt), batch_size):
        batch = paragraps_txt[i:i + batch_size]
        print(f"Processing batch {i // batch_size + 1} ({len(batch)} paragraphs)")

        try:
            batch_summaries = abstractive_summarization_with_quota(batch, estimate_tokens(str(batch)) * 2)

            # Ensure we got the right number of summaries
            if len(batch_summaries) != len(batch):
                print(f"Warning: Expected {len(batch)} summaries, got {len(batch_summaries)}")
                # Pad or trim as needed
                while len(batch_summaries) < len(batch):
                    batch_summaries.append(f"[Summary unavailable for item {len(batch_summaries) + 1}]")
                batch_summaries = batch_summaries[:len(batch)]

            all_summaries.extend(batch_summaries)

            # Mandatory delay between batches for free tier
            if i + batch_size < len(paragraps_txt):
                print("Waiting between batches...")
                time.sleep(8)  # 8 second delay between batches

        except Exception as e:
            print(f"Batch failed: {e}")
            all_summaries.extend([f"[Summary {j + 1} unavailable]" for j in range(len(batch))])

    return all_summaries


def api_to_gemini(passage: str, characters: list[Entity]) -> dict[str, dict[str, str]]:
    """Quota-aware character extraction"""

    # Estimate tokens
    text_content = passage + str([char.name for char in characters])
    estimated_tokens = estimate_tokens(text_content) * 2

    # Check quota
    can_request, wait_time = quota_manager.can_make_request(estimated_tokens)

    if not can_request:
        if wait_time is None:
            print("Daily quota exceeded for character extraction")
            return {}
        else:
            print(f"Waiting {wait_time:.1f} seconds for character extraction...")
            time.sleep(wait_time + 1)

    # Shorter prompt for efficiency
    charsWithNicks = [f"{char.name}" for char in characters]  # Simplified

    prompt = f"""
Extract character appearances from passage as JSON:
{{"character_name": {{"feature": "description"}}}}

Characters: {charsWithNicks}

Passage (first 1000 chars):
{passage[:1000]}{"..." if len(passage) > 1000 else ""}
"""

    try:
        client = genai.Client(api_key=config["services"]["google_gemini"]["api_key"])

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[prompt],
        )

        # Record successful request
        quota_manager.record_request(estimated_tokens)

        text = response.candidates[0].content.parts[0].text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()

        try:
            parsed_json = json.loads(text)
            if isinstance(parsed_json, dict):
                return parsed_json
        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {text}")

        return {}

    except Exception as e:
        error_str = str(e)

        if "429" in error_str or "quota" in error_str.lower():
            print("Character extraction quota exceeded")

        print(f"Character extraction error: {e}")
        return {}


def parse_gemini_list_response(response_text: str, expected_count: int = None) -> List[str]:
    """Parse Gemini's response - improved version with better JSON handling"""
    try:
        cleaned_text = response_text.strip()
        print(f"Parsing response (expected {expected_count} items): {cleaned_text[:200]}...")

        # Remove markdown code blocks if present
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text.replace("```json", "").replace("```", "").strip()
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.replace("```", "").strip()

        # Try to parse as JSON first
        try:
            parsed = json.loads(cleaned_text)
            if isinstance(parsed, list):
                result = [str(item).strip() for item in parsed if str(item).strip()]
                print(f"Successfully parsed JSON with {len(result)} items")
                return result
        except json.JSONDecodeError as e:
            print(f"JSON parse failed: {e}")

        # Try to extract JSON array from text
        json_match = re.search(r'\[(.*?)\]', cleaned_text, re.DOTALL)
        if json_match:
            array_content = json_match.group(0)  # Get the whole match including brackets
            try:
                parsed = json.loads(array_content)
                if isinstance(parsed, list):
                    result = [str(item).strip() for item in parsed if str(item).strip()]
                    print(f"Successfully extracted and parsed JSON array with {len(result)} items")
                    return result
            except json.JSONDecodeError:
                print("Failed to parse extracted JSON array")

        # Fallback: Try to manually parse comma-separated values within brackets
        if json_match:
            content = json_match.group(1)  # Content inside brackets
            items = []

            # Split by comma but be careful with quotes
            current_item = ""
            in_quotes = False
            quote_char = None

            for char in content:
                if char in ['"', "'"] and not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char and in_quotes:
                    in_quotes = False
                    quote_char = None
                elif char == ',' and not in_quotes:
                    item = current_item.strip().strip('"\'')
                    if item:
                        items.append(item)
                    current_item = ""
                    continue

                current_item += char

            # Don't forget the last item
            if current_item.strip():
                item = current_item.strip().strip('"\'')
                if item:
                    items.append(item)

            if items:
                print(f"Successfully parsed manually with {len(items)} items")
                return items

        # Final fallback: split by lines and clean
        lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
        if lines:
            # Remove any numbered prefixes or bullet points
            cleaned_lines = []
            for line in lines:
                # Remove leading numbers, bullets, quotes
                cleaned_line = re.sub(r'^\d+\.\s*', '', line)
                cleaned_line = re.sub(r'^[-*•]\s*', '', cleaned_line)
                cleaned_line = cleaned_line.strip('"\'')
                if cleaned_line:
                    cleaned_lines.append(cleaned_line)

            if cleaned_lines:
                print(f"Using line-based fallback with {len(cleaned_lines)} items")
                return cleaned_lines

        # Last resort: return the whole response as single item
        if cleaned_text:
            print("Using whole response as single item")
            return [cleaned_text]

        print("No content found to parse")
        return []

    except Exception as e:
        print(f"Parse error: {e}")
        # Return the original text as fallback
        return [response_text.strip()] if response_text.strip() else []