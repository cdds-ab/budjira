"""Tests for project metadata models."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from budjira.models.project_metadata import (
    FieldMetadata,
    IssueTypeMetadata,
    ProjectMetadata,
)


class TestFieldMetadata:
    """Test FieldMetadata model."""

    def test_create_minimal(self) -> None:
        """Test creating FieldMetadata with minimal fields."""
        field = FieldMetadata(field_id="summary", name="Summary")
        assert field.field_id == "summary"
        assert field.name == "Summary"
        assert field.required is False
        assert field.schema_type == "string"
        assert field.allowed_values == []

    def test_create_full(self) -> None:
        """Test creating FieldMetadata with all fields."""
        field = FieldMetadata(
            field_id="customfield_10001",
            name="Story Points",
            required=True,
            schema_type="number",
            allowed_values=["1", "2", "3", "5", "8"],
        )
        assert field.field_id == "customfield_10001"
        assert field.name == "Story Points"
        assert field.required is True
        assert field.schema_type == "number"
        assert field.allowed_values == ["1", "2", "3", "5", "8"]


class TestIssueTypeMetadata:
    """Test IssueTypeMetadata model."""

    def test_create_minimal(self) -> None:
        """Test creating IssueTypeMetadata with minimal fields."""
        it = IssueTypeMetadata(id="10001", name="Bug")
        assert it.id == "10001"
        assert it.name == "Bug"
        assert it.description == ""
        assert it.subtask is False
        assert it.fields == []

    def test_create_with_fields(self) -> None:
        """Test creating IssueTypeMetadata with fields."""
        fields = [
            FieldMetadata(field_id="summary", name="Summary", required=True),
            FieldMetadata(field_id="priority", name="Priority", required=False),
        ]
        it = IssueTypeMetadata(
            id="10001",
            name="Change Request",
            description="A change to production",
            subtask=False,
            fields=fields,
        )
        assert it.name == "Change Request"
        assert len(it.fields) == 2
        assert it.fields[0].required is True

    def test_subtask_type(self) -> None:
        """Test subtask issue type."""
        it = IssueTypeMetadata(id="10002", name="Sub-task", subtask=True)
        assert it.subtask is True


class TestProjectMetadata:
    """Test ProjectMetadata model."""

    @pytest.fixture
    def sample_metadata(self) -> ProjectMetadata:
        """Create sample project metadata."""
        return ProjectMetadata(
            project_key="TEST",
            project_name="Test Project",
            issue_types=[
                IssueTypeMetadata(
                    id="1",
                    name="Bug",
                    fields=[
                        FieldMetadata(field_id="summary", name="Summary", required=True),
                        FieldMetadata(field_id="priority", name="Priority", required=True),
                        FieldMetadata(field_id="description", name="Description", required=False),
                    ],
                ),
                IssueTypeMetadata(
                    id="2",
                    name="Story",
                    fields=[
                        FieldMetadata(field_id="summary", name="Summary", required=True),
                    ],
                ),
                IssueTypeMetadata(id="3", name="Sub-task", subtask=True),
            ],
            priorities=["FK1", "FK2", "FK3", "FK4"],
            components=["Backend", "Frontend", "Infrastructure"],
            fetched_at=datetime.now(tz=timezone.utc),
        )

    def test_get_issue_type_names(self, sample_metadata: ProjectMetadata) -> None:
        """Test getting list of issue type names."""
        names = sample_metadata.get_issue_type_names()
        assert names == ["Bug", "Story", "Sub-task"]

    def test_get_issue_type_names_empty(self) -> None:
        """Test getting issue type names when none exist."""
        metadata = ProjectMetadata(
            project_key="EMPTY",
            project_name="Empty",
            fetched_at=datetime.now(tz=timezone.utc),
        )
        assert metadata.get_issue_type_names() == []

    def test_get_required_fields(self, sample_metadata: ProjectMetadata) -> None:
        """Test getting required fields for a specific issue type."""
        required = sample_metadata.get_required_fields("Bug")
        assert len(required) == 2
        names = [f.name for f in required]
        assert "Summary" in names
        assert "Priority" in names

    def test_get_required_fields_fewer(self, sample_metadata: ProjectMetadata) -> None:
        """Test getting required fields for issue type with fewer requirements."""
        required = sample_metadata.get_required_fields("Story")
        assert len(required) == 1
        assert required[0].name == "Summary"

    def test_get_required_fields_unknown_type(self, sample_metadata: ProjectMetadata) -> None:
        """Test getting required fields for unknown issue type returns empty."""
        assert sample_metadata.get_required_fields("Unknown") == []

    def test_is_stale_fresh(self, sample_metadata: ProjectMetadata) -> None:
        """Test that recently fetched metadata is not stale."""
        assert sample_metadata.is_stale(ttl_hours=24) is False

    def test_is_stale_expired(self) -> None:
        """Test that old metadata is stale."""
        old_time = datetime.now(tz=timezone.utc) - timedelta(hours=25)
        metadata = ProjectMetadata(
            project_key="TEST",
            project_name="Test",
            fetched_at=old_time,
        )
        assert metadata.is_stale(ttl_hours=24) is True

    def test_is_stale_naive_datetime(self) -> None:
        """Test staleness check with naive datetime (treated as UTC)."""
        old_time = datetime.now(tz=timezone.utc) - timedelta(hours=25)
        naive_time = old_time.replace(tzinfo=None)
        metadata = ProjectMetadata(
            project_key="TEST",
            project_name="Test",
            fetched_at=naive_time,
        )
        assert metadata.is_stale(ttl_hours=24) is True

    def test_serialization_roundtrip(self, sample_metadata: ProjectMetadata) -> None:
        """Test that metadata survives JSON serialization roundtrip."""
        json_str = sample_metadata.model_dump_json()
        restored = ProjectMetadata.model_validate_json(json_str)
        assert restored.project_key == sample_metadata.project_key
        assert restored.project_name == sample_metadata.project_name
        assert len(restored.issue_types) == len(sample_metadata.issue_types)
        assert restored.priorities == sample_metadata.priorities
        assert restored.components == sample_metadata.components
