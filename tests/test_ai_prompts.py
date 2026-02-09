"""Tests for AI prompt definitions, mode filtering, and model routing."""

from ui.side_panel import AI_PROMPTS, MODEL_ROUTING, LayoutMode

# ---------------------------------------------------------------------------
# Prompt definition validation
# ---------------------------------------------------------------------------


class TestPromptDefinitions:
    """Verify all AI_PROMPTS entries have required fields."""

    def test_all_prompts_have_required_fields(self):
        """Every prompt must have label and modes."""
        for i, prompt in enumerate(AI_PROMPTS):
            assert "label" in prompt, f"Prompt {i} missing 'label'"
            assert "modes" in prompt, f"Prompt {i} ({prompt['label']}) missing 'modes'"

    def test_all_prompts_have_prompt_or_action(self):
        """Every prompt must have either 'prompt' or 'action' field."""
        for prompt in AI_PROMPTS:
            has_prompt = "prompt" in prompt and prompt["prompt"] is not None
            has_action = "action" in prompt
            assert has_prompt or has_action, (
                f"Prompt '{prompt['label']}' has neither 'prompt' nor 'action'"
            )

    def test_prompt_count(self):
        """Sanity check: we expect a known number of prompts."""
        assert len(AI_PROMPTS) >= 14

    def test_modes_are_valid(self):
        """All mode values must be 'coding' or 'writing'."""
        valid = {"coding", "writing"}
        for prompt in AI_PROMPTS:
            for mode in prompt["modes"]:
                assert mode in valid, f"Prompt '{prompt['label']}' has invalid mode '{mode}'"


# ---------------------------------------------------------------------------
# Mode categorization
# ---------------------------------------------------------------------------


def _labels_for_mode(mode: str) -> set[str]:
    """Helper: get prompt labels available in a given mode."""
    return {p["label"] for p in AI_PROMPTS if mode in p.get("modes", [])}


class TestModeCategories:
    """Verify prompts are assigned to the correct modes."""

    CODING_ONLY = {"Explain", "Docstring", "Debug", "Fix", "Refactor", "Test"}
    WRITING_ONLY = {"Summarize", "Improve", "Translate", "Expand", "Tone", "Shorten"}
    SHARED = {"Custom", "Examples", "Transfer"}

    def test_coding_only_prompts(self):
        coding = _labels_for_mode("coding")
        for label in self.CODING_ONLY:
            assert label in coding, f"'{label}' should be in coding mode"

    def test_coding_excludes_writing_only(self):
        coding = _labels_for_mode("coding")
        for label in self.WRITING_ONLY:
            assert label not in coding, f"'{label}' should NOT be in coding mode"

    def test_writing_only_prompts(self):
        writing = _labels_for_mode("writing")
        for label in self.WRITING_ONLY:
            assert label in writing, f"'{label}' should be in writing mode"

    def test_writing_excludes_coding_only(self):
        writing = _labels_for_mode("writing")
        for label in self.CODING_ONLY:
            assert label not in writing, f"'{label}' should NOT be in writing mode"

    def test_shared_prompts_in_both_modes(self):
        coding = _labels_for_mode("coding")
        writing = _labels_for_mode("writing")
        for label in self.SHARED:
            assert label in coding, f"'{label}' should be in coding mode"
            assert label in writing, f"'{label}' should be in writing mode"


# ---------------------------------------------------------------------------
# Prompts grid rebuild / mode switching
# ---------------------------------------------------------------------------


class TestPromptsGrid:
    """Verify _rebuild_prompts_grid shows correct buttons per mode."""

    def test_coding_mode_shows_coding_prompts(self, create_side_panel, qtbot):
        panel = create_side_panel(layout_mode=LayoutMode.CODING)
        qtbot.addWidget(panel)

        button_labels = {btn.text() for btn in panel.prompt_buttons}
        # All coding prompts + shared should be present
        for label in TestModeCategories.CODING_ONLY | TestModeCategories.SHARED:
            assert label in button_labels, f"'{label}' not found in coding mode buttons"
        # No writing-only prompts
        for label in TestModeCategories.WRITING_ONLY:
            assert label not in button_labels, f"'{label}' should not be in coding mode"

    def test_writing_mode_shows_writing_prompts(self, create_side_panel, qtbot):
        panel = create_side_panel(layout_mode=LayoutMode.WRITING)
        qtbot.addWidget(panel)

        button_labels = {btn.text() for btn in panel.prompt_buttons}
        for label in TestModeCategories.WRITING_ONLY | TestModeCategories.SHARED:
            assert label in button_labels, f"'{label}' not found in writing mode buttons"
        for label in TestModeCategories.CODING_ONLY:
            assert label not in button_labels, f"'{label}' should not be in writing mode"

    def test_mode_switch_rebuilds_buttons(self, create_side_panel, qtbot):
        panel = create_side_panel(layout_mode=LayoutMode.CODING)
        qtbot.addWidget(panel)

        coding_labels = {btn.text() for btn in panel.prompt_buttons}

        panel.set_layout_mode(LayoutMode.WRITING)
        writing_labels = {btn.text() for btn in panel.prompt_buttons}

        # Labels should differ between modes (different prompts shown)
        assert coding_labels != writing_labels

    def test_mode_switch_emits_signal(self, create_side_panel, qtbot):
        panel = create_side_panel(layout_mode=LayoutMode.CODING)
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.layout_mode_changed, timeout=500) as blocker:
            panel.set_layout_mode(LayoutMode.WRITING)

        assert blocker.args == ["writing"]


# ---------------------------------------------------------------------------
# Model auto-routing
# ---------------------------------------------------------------------------


class TestModelRouting:
    """Verify model auto-routing maps prompts to correct models."""

    def test_quick_prompts_route_to_lightweight(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        quick_model_id = MODEL_ROUTING["quick"]["model_id"]
        for label in MODEL_ROUTING["quick"]["prompts"]:
            model = panel._get_routed_model(label)
            assert model is not None, f"No routing for '{label}'"
            assert model["id"] == quick_model_id, f"'{label}' should route to {quick_model_id}"

    def test_deep_prompts_route_to_heavier(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        deep_model_id = MODEL_ROUTING["deep"]["model_id"]
        for label in MODEL_ROUTING["deep"]["prompts"]:
            model = panel._get_routed_model(label)
            assert model is not None, f"No routing for '{label}'"
            assert model["id"] == deep_model_id, f"'{label}' should route to {deep_model_id}"

    def test_unknown_prompt_returns_none(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        assert panel._get_routed_model("NonexistentPrompt") is None

    def test_manual_selection_overrides_routing(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        # Simulate manual model selection
        custom_model = {"id": "custom:latest", "name": "Custom", "tag": "1B"}
        panel._set_model(custom_model, manual=True)
        assert panel._manual_model_selection is True

        # After manual selection, the model should stay as the custom one
        assert panel.current_model["id"] == "custom:latest"
