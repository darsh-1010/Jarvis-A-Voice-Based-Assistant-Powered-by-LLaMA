# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Unit tests for jarvis.persona — tone-aware persona builder."""

import pytest

from jarvis.persona import TONE_MODIFIERS, TONE_PRESETS, build_persona


class TestBuildPersona:
    """Tests for build_persona() function."""

    def test_professional_tone_contains_formal_language(self) -> None:
        """Professional tone should contain 'formal' or 'authoritative' wording."""
        result = build_persona(tone="professional")
        assert "formal" in result.lower() or "authoritative" in result.lower()

    def test_friendly_tone_contains_warm_language(self) -> None:
        """Friendly tone should use warm, approachable language."""
        result = build_persona(tone="friendly")
        assert "warm" in result.lower() or "conversational" in result.lower()

    def test_sarcastic_tone_contains_wit_language(self) -> None:
        """Sarcastic tone should reference dry wit."""
        result = build_persona(tone="sarcastic")
        assert "wit" in result.lower() or "sarcasm" in result.lower()

    def test_unknown_tone_falls_back_to_professional(self) -> None:
        """An unrecognised tone string should silently default to professional."""
        fallback = build_persona(tone="professional")
        result = build_persona(tone="definitely_not_a_tone")
        assert result == fallback

    def test_custom_override_replaces_entire_persona(self) -> None:
        """A non-empty custom_override should bypass tone entirely."""
        custom = "You are a pirate assistant. Arrr!"
        result = build_persona(tone="professional", custom_override=custom)
        assert result == custom

    def test_whitespace_only_override_is_ignored(self) -> None:
        """Whitespace-only custom_override should not suppress the tone persona."""
        result = build_persona(tone="professional", custom_override="   ")
        assert "J.A.R.V.I.S." in result  # Falls through to tone-based persona

    def test_all_presets_produce_non_empty_persona(self) -> None:
        """Every preset in TONE_PRESETS should produce a non-empty string."""
        for tone in TONE_PRESETS:
            result = build_persona(tone=tone)
            assert len(result) > 100, f"Persona for '{tone}' is suspiciously short"

    def test_tone_modifiers_covers_all_presets(self) -> None:
        """TONE_PRESETS and TONE_MODIFIERS should be in sync."""
        assert set(TONE_PRESETS) == set(TONE_MODIFIERS.keys())

    def test_output_format_rule_always_present(self) -> None:
        """Every persona should include TTS output formatting rules."""
        for tone in TONE_PRESETS:
            result = build_persona(tone=tone)
            assert "text-to-speech" in result or "spoken aloud" in result

    def test_constraints_always_present(self) -> None:
        """Every persona should include safety constraints."""
        for tone in TONE_PRESETS:
            result = build_persona(tone=tone)
            assert "CONSTRAINTS" in result
