import os
from pathlib import Path

from elevenlabs import ElevenLabs, VoiceSettings
from google import genai
from google.genai import types
from dotenv import load_dotenv

from models import CharacterProfile, DialogueOutput, VoiceConfig
from character.manager import character_dir

load_dotenv()

_SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "voice_system.txt").read_text()

_gemini = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
_eleven = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])


def _profile_to_prompt(profile: CharacterProfile, intro_text: str) -> str:
    return f"""CharacterProfile:
Name: {profile.name}
Archetype: {profile.archetype}
Age: {profile.age}
Personality: {', '.join(profile.personality)}
Speech era: {profile.speech_era}
Voice — pitch: {profile.voice_profile.pitch}, pace: {profile.voice_profile.pace}, accent: {profile.voice_profile.accent}, affect: {profile.voice_profile.affect}

Introduction text to synthesize:
"{intro_text}"

Select the best ElevenLabs voice and settings for this character."""


async def _select_voice(profile: CharacterProfile, intro_text: str) -> VoiceConfig:
    response = _gemini.models.generate_content(
        model="gemini-2.0-flash",
        contents=_profile_to_prompt(profile, intro_text),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=VoiceConfig,
            temperature=0.3,
        ),
    )
    return VoiceConfig.model_validate_json(response.text)


def _synthesize(voice_config: VoiceConfig, text: str, character_id: str) -> Path:
    audio = _eleven.text_to_speech.convert(
        voice_id=voice_config.voice_id,
        text=text,
        model_id=voice_config.model_id,
        voice_settings=VoiceSettings(
            stability=voice_config.stability,
            similarity_boost=voice_config.similarity_boost,
            style=voice_config.style,
            use_speaker_boost=voice_config.use_speaker_boost,
        ),
    )

    out_path = character_dir(character_id) / "voice_sample.mp3"
    with open(out_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return out_path


async def run_voice_agent(
    profile: CharacterProfile,
    dialogue_output: DialogueOutput,
) -> tuple[VoiceConfig, Path]:
    """Returns (VoiceConfig selected, path to saved voice_sample.mp3)."""
    voice_config = await _select_voice(profile, dialogue_output.introduction_text)
    voice_path = _synthesize(voice_config, dialogue_output.introduction_text, profile.id)
    return voice_config, voice_path
