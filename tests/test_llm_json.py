from mas_llms import MockLLM


def test_mock_llm_can_generate_structured_patch_plan_json():
    llm = MockLLM()
    text = llm.generate(
        system_prompt="You are a coder.",
        user_prompt=(
            "You must return ONLY valid JSON.\n\n"
            "Target files:\n- docs/AUTONOMOUS_MODE.md\n\n"
            "Current file contents:\nFILE: docs/AUTONOMOUS_MODE.md\n---\n# Autonomous Mode Runbook\n---\n"
        ),
        response_format="json",
    )
    payload = llm.generate_json(
        system_prompt="You are a coder.",
        user_prompt=(
            "You must return ONLY valid JSON.\n\n"
            "Target files:\n- docs/AUTONOMOUS_MODE.md\n\n"
            "Current file contents:\nFILE: docs/AUTONOMOUS_MODE.md\n---\n# Autonomous Mode Runbook\n---\n"
        ),
        response_format="json",
    )
    assert "Troubleshooting" in text
    assert payload["edits"][0]["path"] == "docs/AUTONOMOUS_MODE.md"
