import os
from dotenv import load_dotenv

# Try to load .env, but safely ignore decoding crashes if they happen on cloud engines!
try:
    load_dotenv(override=False)
except Exception:
    pass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
from core.store import store
from core.composer import Composer
from datetime import datetime
import uvicorn

app = FastAPI(title="Vera Bot API")
composer = Composer()
logger = logging.getLogger(__name__)

@app.get("/v1/healthz")
async def healthz():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": "Vera 2.0 Architect",
        "model": "llama-3.3-70b-versatile",
        "bot_name": "Vera 2.0 (Challenge Bot)",
        "capabilities": ["multi-turn", "intent-detection", "cognitive-analysis"],
    }

@app.post("/v1/context")
async def push_context(request: Request):
    data = await request.json()
    scope = data.get("scope")
    cid = data.get("context_id")
    payload = data.get("payload", {})
    store.push_context(scope, cid, payload)
    return {"accepted": True}

@app.post("/v1/tick")
async def tick(request: Request):
    data = await request.json()
    triggers = data.get("available_triggers", [])
    
    responses = []
    for trigger in triggers:
        try:
            merchant_id = trigger.get("payload", {}).get("merchant_id")
            customer_id = trigger.get("payload", {}).get("customer_id")
            category_slug = trigger.get("payload", {}).get("category")
            
            merchant_ctx = store.get_merchant_context(merchant_id)
            if not category_slug and merchant_ctx:
                category_slug = merchant_ctx.get("category_slug")
                
            category_ctx = store.get_category_context(category_slug)
            customer_ctx = store.customers.get(customer_id) if customer_id else None
            
            # Compose message for trigger
            msg_payload = composer.compose(
                category=category_ctx,
                merchant=merchant_ctx,
                trigger=trigger,
                customer=customer_ctx
            )
            
            msg_payload["trigger_id"] = trigger.get("id")
            msg_payload["merchant_id"] = merchant_id
            responses.append(msg_payload)
        except Exception as e:
            logger.error(f"Error processing trigger {trigger.get('id')}: {e}")
            
    return {"actions": responses}

@app.post("/v1/reply")
async def reply(request: Request):
    data = await request.json()
    merchant_id = data.get("merchant_id")
    message = data.get("message", "").lower()
    
    if "automated" in message or "auto-reply" in message or "thank you for contacting" in message:
         return {
            "body": "No worries, I see this is an auto-reply. I'll reach out directly to the owner later. Best wishes!",
            "cta": "none",
            "send_as": "vera",
            "suppression_key": "auto-reply-exit",
            "action": "end",
            "rationale": "Auto-reply detected, graceful exit to save turns."
        }

    if "stop" in message or "spam" in message or "useless" in message or "unsubscribe" in message:
        return {
            "body": "Sorry! I understand. I'll take a step back and won't message you further. Have a great day!",
            "cta": "none",
            "send_as": "vera",
            "suppression_key": "hostile-exit",
            "action": "end",
            "rationale": "Hostility detected. Exiting engagement."
        }

    if "yes" in message or "let's do it" in message or "whats next" in message or "ok" in message:
        return {
            "body": "Done! Proceeding with the updates. I'll confirm as soon as the changes go live.",
            "cta": "none",
            "send_as": "vera",
            "suppression_key": "intent-actioned",
            "action": "send",
            "rationale": "Clear positive intent detected. Transitioning to action mode."
        }
        
    return {
        "body": "Got it! Adding this to your dashboard notes.",
        "cta": "none",
        "action": "send",
        "send_as": "vera",
        "suppression_key": "reply-handled",
        "rationale": "Default intent handler"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
