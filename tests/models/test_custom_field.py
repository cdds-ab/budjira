"""Tests for custom field models."""

# mypy: disable-error-code="comparison-overlap,arg-type"
# Pydantic models coerce string values to enums during validation

import pytest
from budjira.models.custom_field import CustomFieldConfig, CustomFieldType
from pydantic import ValidationError


class TestCustomFieldType:
    """Test CustomFieldType enum."""

    def test_all_types_exist(self) -> None:
        """Test that all expected field types are defined."""
        assert CustomFieldType.TEXT == "text"
        assert CustomFieldType.SELECT == "select"
        assert CustomFieldType.MULTI_SELECT == "multi_select"
        assert CustomFieldType.USER == "user"
        assert CustomFieldType.DATE == "date"
        assert CustomFieldType.NUMBER == "number"

    def test_type_count(self) -> None:
        """Test that we have exactly 6 field types."""
        assert len(CustomFieldType) == 6


class TestCustomFieldConfig:
    """Test CustomFieldConfig model."""

    def test_create_minimal_config(self) -> None:
        """Test creating config with only required field."""
        config = CustomFieldConfig(field_id="customfield_10001")

        assert config.field_id == "customfield_10001"
        assert config.type == CustomFieldType.TEXT
        assert config.required is False
        assert config.default is None
        assert config.options is None
        assert config.label is None

    def test_create_full_config(self) -> None:
        """Test creating config with all fields."""
        config = CustomFieldConfig(
            field_id="customfield_10002",
            type=CustomFieldType.SELECT,
            required=True,
            default="Infrastructure",
            options=["Infrastructure", "Application", "Database"],
            label="Affected System",
        )

        assert config.field_id == "customfield_10002"
        assert config.type == CustomFieldType.SELECT
        assert config.required is True
        assert config.default == "Infrastructure"
        assert config.options == ["Infrastructure", "Application", "Database"]
        assert config.label == "Affected System"

    def test_field_id_pattern_valid(self) -> None:
        """Test valid field ID patterns."""
        valid_ids = [
            "customfield_1",
            "customfield_10001",
            "customfield_99999",
            "customfield_123456789",
        ]

        for field_id in valid_ids:
            config = CustomFieldConfig(field_id=field_id)
            assert config.field_id == field_id

    def test_field_id_pattern_invalid(self) -> None:
        """Test invalid field ID patterns."""
        invalid_ids = [
            "customfield_",  # No number
            "customfield_abc",  # Letters instead of numbers
            "custom_10001",  # Wrong prefix
            "CUSTOMFIELD_10001",  # Wrong case
            "customfield10001",  # Missing underscore
            "10001",  # No prefix
            "",  # Empty
        ]

        for field_id in invalid_ids:
            with pytest.raises(ValidationError, match="Invalid field_id"):
                CustomFieldConfig(field_id=field_id)

    def test_options_cannot_be_empty_list(self) -> None:
        """Test that options cannot be an empty list if provided."""
        with pytest.raises(ValidationError, match="Options list cannot be empty"):
            CustomFieldConfig(field_id="customfield_10001", options=[])

    def test_options_can_be_none(self) -> None:
        """Test that options can be None."""
        config = CustomFieldConfig(field_id="customfield_10001", options=None)
        assert config.options is None

    def test_type_from_string(self) -> None:
        """Test that type can be set from string value."""
        config = CustomFieldConfig(field_id="customfield_10001", type="select")
        assert config.type == CustomFieldType.SELECT


class TestCustomFieldConfigFormatValue:
    """Test CustomFieldConfig.format_value() method."""

    def test_format_text(self) -> None:
        """Test formatting text field value."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.TEXT)
        assert config.format_value("Hello World") == "Hello World"

    def test_format_select(self) -> None:
        """Test formatting select field value."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.SELECT)
        assert config.format_value("Infrastructure") == {"value": "Infrastructure"}

    def test_format_multi_select_single(self) -> None:
        """Test formatting multi-select field with single value."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.MULTI_SELECT)
        assert config.format_value("Option1") == [{"value": "Option1"}]

    def test_format_multi_select_multiple(self) -> None:
        """Test formatting multi-select field with multiple values."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.MULTI_SELECT)
        result = config.format_value("Option1, Option2, Option3")
        assert result == [{"value": "Option1"}, {"value": "Option2"}, {"value": "Option3"}]

    def test_format_multi_select_with_whitespace(self) -> None:
        """Test formatting multi-select handles whitespace."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.MULTI_SELECT)
        result = config.format_value("  Option1  ,  Option2  ")
        assert result == [{"value": "Option1"}, {"value": "Option2"}]

    def test_format_user(self) -> None:
        """Test formatting user field value."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.USER)
        assert config.format_value("abc123def456") == {"accountId": "abc123def456"}

    def test_format_date(self) -> None:
        """Test formatting date field value."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.DATE)
        assert config.format_value("2024-01-15") == "2024-01-15"

    def test_format_number_integer(self) -> None:
        """Test formatting number field with integer."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.NUMBER)
        assert config.format_value("42") == 42

    def test_format_number_float(self) -> None:
        """Test formatting number field with float."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.NUMBER)
        assert config.format_value("3.14") == 3.14

    def test_format_number_invalid(self) -> None:
        """Test formatting number field with invalid value returns string."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.NUMBER)
        assert config.format_value("not-a-number") == "not-a-number"


class TestCustomFieldConfigValidateValue:
    """Test CustomFieldConfig.validate_value() method."""

    def test_validate_text_always_valid(self) -> None:
        """Test that text fields always validate."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.TEXT)
        is_valid, error = config.validate_value("any value")
        assert is_valid is True
        assert error is None

    def test_validate_select_with_options_valid(self) -> None:
        """Test validating select field with valid option."""
        config = CustomFieldConfig(
            field_id="customfield_10001",
            type=CustomFieldType.SELECT,
            options=["A", "B", "C"],
        )
        is_valid, error = config.validate_value("A")
        assert is_valid is True
        assert error is None

    def test_validate_select_with_options_invalid(self) -> None:
        """Test validating select field with invalid option."""
        config = CustomFieldConfig(
            field_id="customfield_10001",
            type=CustomFieldType.SELECT,
            options=["A", "B", "C"],
        )
        is_valid, error = config.validate_value("D")
        assert is_valid is False
        assert error is not None
        assert "Invalid option" in error
        assert "D" in error

    def test_validate_select_without_options(self) -> None:
        """Test validating select field without options defined."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.SELECT)
        is_valid, error = config.validate_value("anything")
        assert is_valid is True
        assert error is None

    def test_validate_multi_select_all_valid(self) -> None:
        """Test validating multi-select with all valid options."""
        config = CustomFieldConfig(
            field_id="customfield_10001",
            type=CustomFieldType.MULTI_SELECT,
            options=["A", "B", "C"],
        )
        is_valid, error = config.validate_value("A, B")
        assert is_valid is True
        assert error is None

    def test_validate_multi_select_some_invalid(self) -> None:
        """Test validating multi-select with some invalid options."""
        config = CustomFieldConfig(
            field_id="customfield_10001",
            type=CustomFieldType.MULTI_SELECT,
            options=["A", "B", "C"],
        )
        is_valid, error = config.validate_value("A, D, E")
        assert is_valid is False
        assert error is not None
        assert "D" in error
        assert "E" in error

    def test_validate_number_valid_integer(self) -> None:
        """Test validating number field with integer."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.NUMBER)
        is_valid, error = config.validate_value("42")
        assert is_valid is True
        assert error is None

    def test_validate_number_valid_float(self) -> None:
        """Test validating number field with float."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.NUMBER)
        is_valid, error = config.validate_value("3.14")
        assert is_valid is True
        assert error is None

    def test_validate_number_invalid(self) -> None:
        """Test validating number field with non-numeric value."""
        config = CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.NUMBER)
        is_valid, error = config.validate_value("not-a-number")
        assert is_valid is False
        assert error is not None
        assert "Invalid number" in error
