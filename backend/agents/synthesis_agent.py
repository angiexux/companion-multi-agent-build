import os
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

from models import (
    CharacterProfile, DialogueOutput, VisualPrompt,
    VoiceConfig, RelationshipMap, SynthesisOutput,
)

load_dotenv()

_SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "synthesis_system.txt").read_text(
    encoding="utf-8"
)
_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def _build_prompt(
    profile: CharacterProfile,
    visual_prompt: VisualPrompt,
    voice_config: VoiceConfig,
    dialogue_output: DialogueOutput,
    relationship_map: RelationshipMap,
) -> str:
    return f"""Character: {profile.name}

BIO SUMMARY
  Appearance: {profile.appearance}
  Personality: {', '.join(profile.personality)}
  Speech era: {profile.speech_era}
  Voice profile: pitch={profile.voice_profile.pitch}, accent={profile.voice_profile.accent}

IMAGE PROMPT USED
  {visual_prompt.prompt}

VOICE SETTINGS CHOSEN
  Voice: {voice_config.voice_name} (id={voice_config.voice_id})
  Stability: {voice_config.stability}, Style: {voice_config.style}
  Reasoning: {voice_config.reasoning}

STYLE GUIDE HIGHLIGHTS
  Core principle: {dialogue_output.core_principle}
  Forbidden words: {', '.join(dialogue_output.forbidden_words)}
  Must-use words: {', '.join(dialogue_output.must_use_words)}

RELATIONSHIP MAP
  Rivals: {'; '.join(relationship_map.rivals) or 'none'}
  Servants: {'; '.join(relationship_map.servants) or 'none'}
  Notes: {relationship_map.notes}

Check all artifacts for consistency and return a SynthesisOutput."""


async def run_synthesis_agent(
    profile: CharacterProfile,
    visual_prompt: VisualPrompt,
    voice_config: VoiceConfig,
    dialogue_output: DialogueOutput,
    relationship_map: RelationshipMap,
) -> SynthesisOutput:
    prompt = _build_prompt(profile, visual_prompt, voice_config, dialogue_output, relationship_map)

    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=SynthesisOutput,
            temperature=0.2,
        ),
    )
    return SynthesisOutput.model_validate_json(response.text)
