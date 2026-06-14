from abc import ABC, abstractmethod
from typing import Any


class BaseJobParser(ABC):
    """
    Parses raw payload into company-native job records.

    Output is a list of dictionaries preserving each site's original field
    names and structure. No normalization happens here.
    """

    @abstractmethod
    def parse(self, raw_payload: Any) -> list[dict[str, Any]]:
        """Extract job records using company-specific page structure."""
