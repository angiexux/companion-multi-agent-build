import json
import os
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

from models import CharacterProfile, DialogueOutput

load_dotenv()

_SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "dialogue_system.txt").read_text(
    encoding="utf-8"
)

_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def _profile_to_prompt(profile: CharacterProfile) -> str:
    return f"""CharacterProfile:
Name: {profile.name}
Archetype: {profile.archetype}
Age: {profile.age}
Origin: {profile.origin}
Personality: {', '.join(profile.personality)}
Backstory: {profile.backstory}
Fears: {'; '.join(profile.fears)}
Desires: {'; '.join(profile.desires)}
Speech era: {profile.speech_era}
Voice — pitch: {profile.voice_profile.pitch}, pace: {profile.voice_profile.pace}, accent: {profile.voice_profile.accent}, affect: {profile.voice_profile.affect}

Generate the style guide and introduction text for this character."""


async def run_dialogue_agent(profile: CharacterProfile) -> tuple[DialogueOutput, str]:
    """
    Returns (DialogueOutput, style_guide_markdown).
    The markdown is saved to style_guide.md; DialogueOutput is used by VoiceAgent for intro text.
    """
    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        contents=_profile_to_prompt(profile),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=DialogueOutput,
            temperature=0.85,
        ),
    )

    output = DialogueOutput.model_validate_json(response.text)
    style_md = _render_style_guide(profile, output)
    return output, style_md


def _render_style_guide(profile: CharacterProfile, output: DialogueOutput) -> str:
    exchanges = "\n\n".join(
        f'User: "{ex.user}"\n{profile.name}: "{ex.character}"'
        for ex in output.example_exchanges
    )

    emotional = "\n".join(
        f"- **{emotion}:** {phrasing}"
        for emotion, phrasing in output.emotional_range.items()
    )

    specialist = (
        f"\n**Specialist/archaic terms:** {', '.join(output.specialist_terms)}"
        if output.specialist_terms else ""
    )

    return f"""# {profile.name} — Dialogue Style Guide

## Core principle
{output.core_principle}

## Speech patterns
{chr(10).join(f'- {p}' for p in output.patterns)}

## Vocabulary
**Must use:** {', '.join(output.must_use_words)}
**Forbidden:** {', '.join(output.forbidden_words)}{specialist}

## Emotional range
{emotional}

## Example exchanges
{exchanges}
"""
