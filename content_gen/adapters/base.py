from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from ..core.schemas import ProcessedQuestion, Flashcard


class BaseStorageAdapter(ABC):
    """
    Abstract Base Class for Edmate Storage Adapters.
    Allows the pipeline to be decoupled from specific database schemas.
    """

    @abstractmethod
    def save_question(self, question: ProcessedQuestion) -> str:
        """Saves a single question and returns its unique ID."""
        pass

    @abstractmethod
    def save_flashcards(self, flashcards: List[Flashcard], context: Dict[str, Any]) -> int:
        """Saves a batch of flashcards and returns the count of inserted records."""
        pass

    @abstractmethod
    def get_question(self, question_id: str) -> Optional[ProcessedQuestion]:
        """Retrieves a question by its ID."""
        pass

    @abstractmethod
    def resolve_metadata(self, hint: str, type: str) -> Optional[str]:
        """Resolves topic, subject, or grade IDs from names/hints."""
        pass
