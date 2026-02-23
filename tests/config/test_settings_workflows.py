"""Tests for workflow profile loading and saving in settings."""

from pathlib import Path
from unittest.mock import patch

from budjira.config.settings import Settings
from budjira.models.workflow import (
    OverbookingPolicy,
    ProjectMapping,
    ShadowTicketStrategy,
    WorkflowProfile,
    WorkflowProfileList,
)


class TestSettingsWorkflows:
    """Test settings workflow profile management."""

    def test_workflows_property_returns_empty_list_when_no_file(self, tmp_path: Path) -> None:
        """Test that workflows property returns empty list when no file exists."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            settings = Settings()
            workflows = settings.workflows
            assert isinstance(workflows, WorkflowProfileList)
            assert workflows.profiles == []

    def test_save_and_load_workflows(self, tmp_path: Path) -> None:
        """Test saving and loading workflow profiles roundtrip."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            settings = Settings()

            profile = WorkflowProfile(
                name="ek-to-k",
                planning_connection="ek-planning",
                booking_connection="k-booking",
                project_mappings=[
                    ProjectMapping(planning_project="EK", booking_project="K"),
                    ProjectMapping(planning_project="EK2", booking_project="K2"),
                ],
                shadow_strategy=ShadowTicketStrategy.SUMMARY_SEARCH,
                overbooking_policy=OverbookingPolicy.CONFIRM,
            )

            workflows = WorkflowProfileList()
            workflows.add(profile)
            settings.save_workflows(workflows)

            # Verify file was written
            assert settings.workflows_file.exists()

            # Clear cache and reload
            settings._workflows = None
            loaded = settings.load_workflows()

            assert len(loaded.profiles) == 1
            loaded_profile = loaded.profiles[0]
            assert loaded_profile.name == "ek-to-k"
            assert loaded_profile.planning_connection == "ek-planning"
            assert loaded_profile.booking_connection == "k-booking"
            assert len(loaded_profile.project_mappings) == 2
            assert loaded_profile.project_mappings[0].planning_project == "EK"
            assert loaded_profile.project_mappings[0].booking_project == "K"
            assert loaded_profile.shadow_strategy == ShadowTicketStrategy.SUMMARY_SEARCH
            assert loaded_profile.overbooking_policy == OverbookingPolicy.CONFIRM

    def test_workflows_caching(self, tmp_path: Path) -> None:
        """Test that workflows are cached after first load."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            settings = Settings()
            workflows1 = settings.workflows
            workflows2 = settings.workflows
            assert workflows1 is workflows2

    def test_save_workflows_updates_cache(self, tmp_path: Path) -> None:
        """Test that saving workflows updates the cache."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            settings = Settings()
            new_workflows = WorkflowProfileList()
            new_workflows.add(
                WorkflowProfile(
                    name="test",
                    planning_connection="plan",
                    booking_connection="book",
                )
            )
            settings.save_workflows(new_workflows)
            assert settings._workflows is new_workflows
