import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from prompts.templates import ANALYSIS_PROMPT, GENERATION_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Groq via the OpenAI Python SDK
# Fallback to OPENAI_API_KEY in case GROQ_API_KEY isn't found to bypass the strict init check
api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or ""

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

def call_llm(system_prompt: str, user_content: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            temperature=0.2,
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"LLM Call Failed: {e}")
        return {}

class Composer:
    def compose(self, category: dict, merchant: dict, trigger: dict, customer: dict = None) -> dict:
        # Avoid empty dicts causing issues
        customer_ctx = customer or {}

        # -----------------------------
        # STAGE 1: Cognitive Analysis
        # -----------------------------
        user_prompt_1 = ANALYSIS_PROMPT.format(
            category_json=json.dumps(category),
            merchant_json=json.dumps(merchant),
            trigger_json=json.dumps(trigger),
            customer_json=json.dumps(customer_ctx)
        )
        
        analysis_strategy = call_llm("Analyze the data and determine the strategy.", user_prompt_1)
        
        # -----------------------------
        # STAGE 2: Message Generation
        # -----------------------------
        voice_profile = category.get("voice", "professional and helpful")
        merchant_name = merchant.get("identity", {}).get("owner_first_name", "Merchant")
        trigger_kind = trigger.get("kind", "periodic_update")
        
        user_prompt_2 = GENERATION_PROMPT.format(
            analysis_json=json.dumps(analysis_strategy),
            voice_profile=json.dumps(voice_profile),
            merchant_name=merchant_name,
            trigger_kind=trigger_kind
        )

        final_msg = call_llm("Generate the final message adhering to constraints.", user_prompt_2)
        
        # Ensure fallback
        if not final_msg or "body" not in final_msg:
            return {
                "body": f"Hi {merchant_name}, Vera here. Just wanted to share a quick update on your profile performance. Should I send the details?",
                "cta": "binary",
                "send_as": "vera",
                "suppression_key": trigger.get("suppression_key", "fallback"),
                "rationale": "Fallback safety response."
            }
            
        final_msg["send_as"] = "merchant_on_behalf" if customer else "vera"
        final_msg["suppression_key"] = trigger.get("suppression_key", trigger.get("id"))
        return final_msg
