import os
import json
import hashlib
import re
from typing import List, Dict, Tuple
from django.core.cache import cache
from django.conf import settings
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

class RecipeStepAnalyzer:
    """Cost-optimized GPT service for recipe step analysis with robust JSON handling"""

    def __init__(self):
        self.model = "gpt-4o"
        self.max_tokens = 800  # Increased for better responses
        self.temperature = 0.1
        self.enabled = bool(getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY')))
        
        if self.enabled:
            self.client = OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY')))
        else:
            logger.warning("OpenAI API key not found. GPT features will be disabled.")

    def _get_cache_key(self, text: str, analysis_type: str) -> str:
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"recipe_gpt_{analysis_type}_{text_hash}"

    def _clean_json_response(self, response_text: str) -> str:
        """Clean and fix common JSON issues in GPT responses"""
        if not response_text:
            return "{}"
        
        # Remove any markdown code blocks
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        
        # Remove any leading/trailing whitespace
        response_text = response_text.strip()
        
        # Find JSON object boundaries
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            logger.error("No valid JSON object found in response")
            return "{}"
        
        json_text = response_text[start_idx:end_idx + 1]
        
        # Fix common issues
        # Fix trailing commas
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        
        return json_text

    def _call_gpt_api(self, prompt: str, cache_key: str) -> Dict:
        """Make cost-optimized GPT API call with robust error handling"""
        if not self.enabled:
            logger.warning("OpenAI GPT is not enabled.")
            return None

        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Using cached GPT result for {cache_key}")
            return cached_result

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional chef assistant. Always respond with valid JSON only. No additional text or explanations. Ensure all strings are properly escaped."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=15,
            )
            
            raw_content = response.choices[0].message.content.strip()
            logger.info(f"Raw GPT response: {raw_content[:200]}...")
            
            # Clean and parse JSON
            cleaned_json = self._clean_json_response(raw_content)
            try:
                result = json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse cleaned JSON: {e}")
                logger.error(f"Cleaned JSON: {cleaned_json}")
                # Try to extract partial data
                result = self._extract_partial_json(cleaned_json)
                if not result:
                    return None
            
            # Cache successful result
            cache.set(cache_key, result, 60 * 60 * 24 * 30)
            
            # Log token usage for cost tracking
            if hasattr(response, 'usage') and response.usage:
                logger.info(f"GPT API call: {response.usage.total_tokens} tokens used")
            else:
                logger.info("GPT API call completed (token count unavailable)")
            
            return result

        except Exception as e:
            logger.error(f"GPT API call failed: {e}")
            return None

    def _extract_partial_json(self, json_text: str) -> Dict:
        """Attempt to extract partial data from malformed JSON"""
        try:
            # Try to extract key-value pairs using regex
            result = {}
            
            # Extract steps array if present
            steps_match = re.search(r'"steps"\s*:\s*\[(.*?)\]', json_text, re.DOTALL)
            if steps_match:
                steps_content = steps_match.group(1)
                steps = []
                
                # Extract individual step objects
                step_matches = re.findall(r'\{([^}]*)\}', steps_content)
                for i, step_match in enumerate(step_matches):
                    step = {'number': i + 1}
                    
                    # Extract text
                    text_match = re.search(r'"text"\s*:\s*"([^"]*)"', step_match)
                    if text_match:
                        step['text'] = text_match.group(1)
                    
                    # Extract time
                    time_match = re.search(r'"time_minutes"\s*:\s*(\d+)', step_match)
                    if time_match:
                        step['time_minutes'] = int(time_match.group(1))
                    else:
                        step['time_minutes'] = 5
                    
                    # Extract type
                    type_match = re.search(r'"type"\s*:\s*"([^"]*)"', step_match)
                    if type_match:
                        step['type'] = type_match.group(1)
                    else:
                        step['type'] = 'prep'
                    
                    if 'text' in step:
                        steps.append(step)
                
                result['steps'] = steps
            
            # Extract cooking times
            prep_match = re.search(r'"prep_minutes"\s*:\s*(\d+)', json_text)
            if prep_match:
                result['prep_minutes'] = int(prep_match.group(1))
            
            cook_match = re.search(r'"cook_minutes"\s*:\s*(\d+)', json_text)
            if cook_match:
                result['cook_minutes'] = int(cook_match.group(1))
            
            # Extract category
            category_match = re.search(r'"category"\s*:\s*"([^"]*)"', json_text)
            if category_match:
                result['category'] = category_match.group(1)
            
            return result if result else None
            
        except Exception as e:
            logger.error(f"Failed to extract partial JSON: {e}")
            return None

    def analyze_recipe_steps(self, instructions: str, recipe_title: str = "") -> List[Dict]:
        """Parse recipe instructions into structured steps with time estimates"""
        if not self.enabled or not instructions:
            return self._fallback_step_parsing(instructions)

        # Truncate very long instructions to control costs
        if len(instructions) > 1500:
            instructions = instructions[:1500] + "..."

        cache_key = self._get_cache_key(instructions, "steps_and_timing")

        # Improved prompt with explicit JSON structure
        prompt = f"""Parse this recipe into numbered steps with time estimates.
Return ONLY valid JSON in this exact format:
{{"steps": [{{"text": "step description", "time_minutes": 5, "type": "prep"}}]}}

Instructions: {instructions[:1000]}"""

        result = self._call_gpt_api(prompt, cache_key)

        if result and 'steps' in result:
            return self._validate_and_clean_steps(result['steps'])
        else:
            logger.warning("GPT step parsing failed, using fallback")
            return self._fallback_step_parsing(instructions)

    def estimate_cooking_times(self, recipe_data: Dict) -> Tuple[int, int]:
        """Estimate prep and cook times for a recipe"""
        if not self.enabled:
            return 15, 30  # Default fallback

        # Build minimal context
        context_parts = []
        if recipe_data.get('title'):
            context_parts.append(f"Recipe: {recipe_data['title'][:50]}")
        if recipe_data.get('category'):
            context_parts.append(f"Type: {recipe_data['category']}")
        
        ingredients_count = len(recipe_data.get('ingredients', []))
        if ingredients_count:
            context_parts.append(f"Ingredients: {ingredients_count}")

        context = ". ".join(context_parts)
        cache_key = self._get_cache_key(context, "cooking_times")

        # Simplified prompt
        prompt = f"""Estimate cooking times for this recipe.
Return ONLY valid JSON: {{"prep_minutes": 15, "cook_minutes": 30}}

{context[:150]}"""

        result = self._call_gpt_api(prompt, cache_key)

        if result and 'prep_minutes' in result and 'cook_minutes' in result:
            prep_time = max(5, min(120, result['prep_minutes']))
            cook_time = max(5, min(240, result['cook_minutes']))
            return prep_time, cook_time

        return 15, 30  # Fallback

    def categorize_recipe(self, recipe_data: Dict) -> str:
        """Determine recipe category if missing"""
        if not self.enabled:
            return "Miscellaneous"

        # Only use if category is truly missing or unclear
        existing_category = recipe_data.get('category', '').strip()
        if existing_category and existing_category != "Miscellaneous":
            return existing_category

        # Build context from title and ingredients
        title = recipe_data.get('title', '')[:100]
        ingredients = recipe_data.get('ingredients', [])[:10]
        ingredient_names = [ing['name'][:20] for ing in ingredients if isinstance(ing, dict)]

        context = f"Title: {title}. Ingredients: {', '.join(ingredient_names[:5])}"
        cache_key = self._get_cache_key(context, "category")

        # Simplified prompt with limited options
        prompt = f"""Categorize this recipe. Choose ONE from: Breakfast, Dessert, Beef, Chicken, Seafood, Pasta, Vegetarian, Vegan, Side, Starter, Miscellaneous.
Return ONLY valid JSON: {{"category": "category_name"}}

{context[:120]}"""

        result = self._call_gpt_api(prompt, cache_key)

        if result and 'category' in result:
            return result['category']

        return "Miscellaneous"

    def _validate_and_clean_steps(self, steps: List[Dict]) -> List[Dict]:
        """Validate and clean GPT-generated steps"""
        cleaned_steps = []

        for i, step in enumerate(steps[:15]):  # Max 15 steps
            if not isinstance(step, dict):
                continue

            text = step.get('text', '').strip()
            if not text or len(text) < 5:
                continue

            # Clean and validate time
            time_minutes = step.get('time_minutes', 5)
            if not isinstance(time_minutes, (int, float)) or time_minutes < 1:
                time_minutes = 5
            elif time_minutes > 180:  # Max 3 hours per step
                time_minutes = 180

            step_type = step.get('type', 'prep')
            if step_type not in ['prep', 'cook', 'wait', 'mix', 'serve']:
                step_type = 'prep'

            cleaned_steps.append({
                'number': i + 1,
                'text': text[:500],  # Limit step length
                'time_minutes': int(time_minutes),
                'type': step_type
            })

        return cleaned_steps

    def _fallback_step_parsing(self, instructions: str) -> List[Dict]:
        """Fallback parsing when GPT is not available or fails"""
        if not instructions:
            return []

        import re
        steps = []

        # Split by numbered patterns
        step_patterns = [
            r'\n\d+\.',
            r'\d+\.\s',
            r'STEP \d+',
            r'Step \d+',
        ]

        parts = []
        for pattern in step_patterns:
            if re.search(pattern, instructions, re.IGNORECASE):
                parts = re.split(pattern, instructions, flags=re.IGNORECASE)
                parts = [part.strip() for part in parts if part.strip()]
                if len(parts) > 1:
                    if len(parts[0]) < 50:  # Remove intro text
                        parts = parts[1:]
                    break

        if not parts:
            # Split by double newlines
            parts = [p.strip() for p in instructions.split('\n\n') if p.strip()]

        if not parts:
            # Split by periods followed by capital letters
            parts = re.split(r'\.\s+(?=[A-Z])', instructions)
            parts = [p.strip() + '.' for p in parts if len(p.strip()) > 20]

        if not parts:
            # Single long instruction
            parts = [instructions]

        for i, part in enumerate(parts[:12]):  # Max 12 steps
            if len(part) < 10:
                continue

            # Clean up the step text
            part = re.sub(r'^\d+\.?\s*', '', part).strip()
            part = re.sub(r'^STEP\s*\d+:?\s*', '', part, flags=re.IGNORECASE).strip()

            # Simple time estimation
            time_estimate = 5
            part_lower = part.lower()
            if any(word in part_lower for word in ['bake', 'roast', 'cook', 'simmer', 'boil']):
                time_estimate = 25
            elif any(word in part_lower for word in ['fry', 'saute', 'brown', 'sear']):
                time_estimate = 8
            elif any(word in part_lower for word in ['mix', 'stir', 'combine', 'whisk']):
                time_estimate = 3
            elif any(word in part_lower for word in ['chop', 'dice', 'cut', 'slice']):
                time_estimate = 6
            elif any(word in part_lower for word in ['chill', 'rest', 'cool', 'refrigerate']):
                time_estimate = 15

            steps.append({
                'number': i + 1,
                'text': part[:500],
                'time_minutes': time_estimate,
                'type': 'prep'
            })

        return steps

# Singleton instance
recipe_analyzer = RecipeStepAnalyzer()