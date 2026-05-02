from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ContextState:
    def __init__(self):
        self.categories: Dict[str, dict] = {}
        self.merchants: Dict[str, dict] = {}
        self.customers: Dict[str, dict] = {}
        self.conversations: Dict[str, list] = {}

    def push_context(self, scope: str, context_id: str, payload: dict):
        if scope == "category":
            self.categories[context_id] = payload
        elif scope == "merchant":
            self.merchants[context_id] = payload
        elif scope == "customer":
            self.customers[context_id] = payload

    def get_merchant_context(self, merchant_id: str):
        return self.merchants.get(merchant_id, {})

    def get_category_context(self, slug: str):
        return self.categories.get(slug, {})

# Global singleton store
store = ContextState()
