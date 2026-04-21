import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class MetricsTracker:
    """
    Tracks LLM usage, tokens, and costs across Edmate sessions.
    Persists data to a local JSON file for UI consumption.
    """
    
    def __init__(self, storage_path: str = "content_gen/data/session_metrics.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics = self._load_metrics()

    def _load_metrics(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return {"total_cost": 0.0, "total_tokens": 0, "last_updated": None, "calls": 0}
        
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {"total_cost": 0.0, "total_tokens": 0, "last_updated": None, "calls": 0}

    def log_usage(self, response_obj: Any):
        """
        Extracts usage data from a LiteLLM response object and updates local metrics.
        """
        # LiteLLM provides usage and cost in the response
        usage = getattr(response_obj, 'usage', {})
        cost = getattr(response_obj, '_response_ms', 0) # Just a placeholder if cost is missing
        
        # Real cost from LiteLLM is usually in response._hidden_params or similar 
        # but LiteLLM also provides it in a more direct way if litellm.ModelResponse is used
        try:
            from litellm import completion_cost
            actual_cost = completion_cost(completion_response=response_obj)
        except Exception:
            actual_cost = 0.0

        self.metrics["total_cost"] += actual_cost
        self.metrics["total_tokens"] += usage.get("total_tokens", 0)
        self.metrics["calls"] += 1
        self.metrics["last_updated"] = datetime.now().isoformat()
        
        self._save_metrics()

    def _save_metrics(self):
        with open(self.storage_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def get_current_cost(self) -> float:
        return self.metrics.get("total_cost", 0.0)

    def reset_if_new_day(self):
        """Placeholder for daily reset logic if needed."""
        pass
