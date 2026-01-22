from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time

class Thought(BaseModel):
    """Represents a single step in the thinking process"""
    thought: str
    thought_number: int
    total_thoughts_estimate: int
    is_revision: bool = False
    revises_thought: Optional[int] = None
    branch_from_thought: Optional[int] = None
    branch_id: Optional[str] = None
    needs_more_thoughts: bool = True
    timestamp: float = Field(default_factory=time.time)

class SequentialThinker:
    """
    Manages a sequence of thoughts, allowing for dynamic updates,
    branching, and revision of previous thoughts.
    """
    def __init__(self):
        self.history: List[Thought] = []
        self.branches: Dict[str, List[Thought]] = {"main": []}
        self.current_branch: str = "main"

    def add_thought(self, 
                    thought_text: str, 
                    total_thoughts_estimate: int, 
                    next_needed: bool = True,
                    branch_id: Optional[str] = None,
                    revises: Optional[int] = None) -> Thought:
        """
        Add a new thought to the sequence.
        """
        thought_num = len(self.history) + 1
        
        # Handle branching
        if branch_id and branch_id != self.current_branch:
            # If switching to a new/different branch
            if branch_id not in self.branches:
                self.branches[branch_id] = []
            self.current_branch = branch_id

        new_thought = Thought(
            thought=thought_text,
            thought_number=thought_num,
            total_thoughts_estimate=total_thoughts_estimate,
            needs_more_thoughts=next_needed,
            branch_id=self.current_branch,
            is_revision=revises is not None,
            revises_thought=revises
        )

        self.history.append(new_thought)
        self.branches[self.current_branch].append(new_thought)
        
        return new_thought

    def get_hypothesis(self) -> str:
        """
        Synthesize the thinking history into a final conclusion/hypothesis.
        This is a simple concatenation for now, but could be more advanced.
        """
        # Filter for the current branch or 'main' if simplistic
        thoughts = self.branches.get(self.current_branch, self.history)
        
        # Basic synthesis: Join thoughts
        steps = [f"{t.thought_number}. {t.thought}" for t in thoughts]
        return "\n".join(steps)

    def get_trajectory(self) -> List[Dict[str, Any]]:
        """Return full history JSON-serializable"""
        return [t.dict() for t in self.history]
