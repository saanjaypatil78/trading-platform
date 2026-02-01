"""
GLM Model Registry
Self-updating configuration for the GLM 4.7 family.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Optional, Dict, Any


@dataclass
class GLMModelRegistry:
    """Tracks the active GLM model and refreshes from environment when changed."""

    default_version: str = "4.7"
    model_name: str = "glm-4.7"
    updated_at: float = time.time()

    def refresh(self) -> str:
        """Reload model metadata from environment variables."""
        version = os.getenv("GLM_MODEL_VERSION", self.default_version)
        model_name = os.getenv("GLM_MODEL_NAME", f"glm-{version}")

        if model_name != self.model_name:
            self.model_name = model_name
            self.updated_at = time.time()

        return self.model_name

    def info(self) -> Dict[str, Any]:
        """Return the current model configuration metadata."""
        self.refresh()
        return {
            "model": self.model_name,
            "model_version": os.getenv("GLM_MODEL_VERSION", self.default_version),
            "base_url": os.getenv("GLM_API_URL"),
            "has_api_key": bool(os.getenv("GLM_API_KEY")),
            "updated_at": self.updated_at,
        }


glm_registry = GLMModelRegistry()
