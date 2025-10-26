"""Tests for output formatting utilities."""

import json
from datetime import date, datetime
from enum import Enum

from budjira.utils.formatter import OutputFormat, OutputFormatter
from pydantic import BaseModel


class SampleEnum(str, Enum):
    """Sample enum for testing."""

    VALUE1 = "value1"
    VALUE2 = "value2"


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""

    name: str
    count: int
    created_at: datetime


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_table_format(self):
        """Test TABLE format value."""
        assert OutputFormat.TABLE.value == "table"

    def test_json_format(self):
        """Test JSON format value."""
        assert OutputFormat.JSON.value == "json"


class TestOutputFormatterJsonSerializer:
    """Tests for JSON serialization."""

    def test_serialize_pydantic_model(self):
        """Test Pydantic model serialization."""
        model = SampleModel(name="test", count=42, created_at=datetime(2025, 10, 26, 12, 0, 0))
        result = json.loads(OutputFormatter.to_json(model))

        assert result["name"] == "test"
        assert result["count"] == 42
        assert result["created_at"] == "2025-10-26T12:00:00"

    def test_serialize_datetime(self):
        """Test datetime serialization to ISO format."""
        data = {"timestamp": datetime(2025, 10, 26, 14, 30, 0)}
        result = json.loads(OutputFormatter.to_json(data))

        assert result["timestamp"] == "2025-10-26T14:30:00"

    def test_serialize_date(self):
        """Test date serialization to ISO format."""
        data = {"date": date(2025, 10, 26)}
        result = json.loads(OutputFormatter.to_json(data))

        assert result["date"] == "2025-10-26"

    def test_serialize_enum(self):
        """Test enum serialization to value."""
        data = {"status": SampleEnum.VALUE1}
        result = json.loads(OutputFormatter.to_json(data))

        assert result["status"] == "value1"

    def test_serialize_list_of_models(self):
        """Test list of Pydantic models serialization."""
        models = [
            SampleModel(name="first", count=1, created_at=datetime(2025, 10, 26, 12, 0, 0)),
            SampleModel(name="second", count=2, created_at=datetime(2025, 10, 26, 13, 0, 0)),
        ]
        result = json.loads(OutputFormatter.to_json(models))

        assert len(result) == 2
        assert result[0]["name"] == "first"
        assert result[1]["name"] == "second"

    def test_serialize_nested_models(self):
        """Test nested Pydantic models serialization."""

        class ParentModel(BaseModel):
            child: SampleModel

        parent = ParentModel(child=SampleModel(name="nested", count=5, created_at=datetime(2025, 10, 26)))
        result = json.loads(OutputFormatter.to_json(parent))

        assert result["child"]["name"] == "nested"
        assert result["child"]["count"] == 5

    def test_serialize_none_values(self):
        """Test None values serialization."""
        data = {"value": None}
        result = json.loads(OutputFormatter.to_json(data))

        assert result["value"] is None

    def test_serialize_empty_list(self):
        """Test empty list serialization."""
        data: list[str] = []
        result = json.loads(OutputFormatter.to_json(data))

        assert result == []

    def test_serialize_empty_dict(self):
        """Test empty dict serialization."""
        data: dict[str, str] = {}
        result = json.loads(OutputFormatter.to_json(data))

        assert result == {}


class TestOutputFormatterToJson:
    """Tests for to_json method."""

    def test_to_json_returns_string(self):
        """Test that to_json returns a string."""
        result = OutputFormatter.to_json({"key": "value"})

        assert isinstance(result, str)

    def test_to_json_default_indent(self):
        """Test default indentation (2 spaces)."""
        result = OutputFormatter.to_json({"key": "value"})

        assert "  " in result  # 2-space indentation

    def test_to_json_custom_indent(self):
        """Test custom indentation."""
        result = OutputFormatter.to_json({"key": "value"}, indent=4)

        assert "    " in result  # 4-space indentation

    def test_to_json_no_indent(self):
        """Test no indentation (compact JSON)."""
        result = OutputFormatter.to_json({"key": "value"}, indent=None)

        assert "\n" not in result  # No newlines in compact JSON


class TestOutputFormatterOutputJson:
    """Tests for output_json method."""

    def test_output_json_prints_to_stdout(self, capsys):
        """Test that output_json prints to stdout."""
        OutputFormatter.output_json({"key": "value"})
        captured = capsys.readouterr()

        assert '"key": "value"' in captured.out

    def test_output_json_with_pydantic_model(self, capsys):
        """Test output_json with Pydantic model."""
        model = SampleModel(name="test", count=42, created_at=datetime(2025, 10, 26))
        OutputFormatter.output_json(model)
        captured = capsys.readouterr()

        assert '"name": "test"' in captured.out
        assert '"count": 42' in captured.out


class TestOutputFormatterIsJsonFormat:
    """Tests for is_json_format method."""

    def test_is_json_format_with_json(self):
        """Test with 'json' string."""
        assert OutputFormatter.is_json_format("json") is True

    def test_is_json_format_with_json_uppercase(self):
        """Test with 'JSON' (case-insensitive)."""
        assert OutputFormatter.is_json_format("JSON") is True

    def test_is_json_format_with_table(self):
        """Test with 'table' string."""
        assert OutputFormatter.is_json_format("table") is False

    def test_is_json_format_with_none(self):
        """Test with None."""
        assert OutputFormatter.is_json_format(None) is False

    def test_is_json_format_with_invalid(self):
        """Test with invalid format string."""
        assert OutputFormatter.is_json_format("xml") is False
