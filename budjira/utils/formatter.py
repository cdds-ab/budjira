"""Output formatting utilities for different output formats (table, JSON)."""

import json
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class OutputFormat(str, Enum):
    """Supported output formats."""

    TABLE = "table"
    JSON = "json"


class OutputFormatter:
    """Format data for different output types (table, JSON)."""

    @staticmethod
    def _json_serializer(obj: Any) -> Any:
        """Custom JSON serializer for non-standard types.

        Handles:
        - Pydantic models → dict
        - datetime/date → ISO string
        - Enum → value
        - Other → str
        """
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        if isinstance(obj, datetime | date):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return str(obj)

    @staticmethod
    def to_json(data: Any, *, indent: int | None = 2) -> str:
        """Serialize data to JSON string.

        Args:
            data: Data to serialize (dict, list, Pydantic model, etc.)
            indent: JSON indentation (default: 2, None for compact)

        Returns:
            JSON string
        """
        return json.dumps(data, indent=indent, default=OutputFormatter._json_serializer, ensure_ascii=False)

    @staticmethod
    def output_json(data: Any, *, indent: int | None = 2) -> None:
        """Output data as JSON to stdout.

        Args:
            data: Data to serialize and output
            indent: JSON indentation (default: 2, None for compact)
        """
        print(OutputFormatter.to_json(data, indent=indent))

    @staticmethod
    def is_json_format(format_str: str | None) -> bool:
        """Check if format is JSON.

        Args:
            format_str: Format string ("json", "table", None)

        Returns:
            True if JSON format
        """
        if format_str is None:
            return False
        return format_str.lower() == OutputFormat.JSON.value
