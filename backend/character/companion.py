"""
CompanionSession — live conversational interface for an activated character.
Streams text chunks and ElevenLabs TTS audio over WebSocket.
"""
import os
from collections.abc import AsyncGenerator

from elevenlabs import ElevenLabs, VoiceSettings
from google import genai
from google.genai import types

from character.manager import load_bio, character_dir
from models import VoiceConfig

_gemini = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
_eleven = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])


class CompanionSession:
    def __init__(self, character_id: str):
        self.character_id = character_id
        self.profile = load_bio(character_id)
        self.voice_config = self._load_voice_config()
        self.style_guide = self._load_style_guide()
        self.history: list[dict] = []
        self._system_prompt = self._build_system_prompt()

    def _load_voice_config(self) -> VoiceConfig:
        import json
        path = character_dir(self.character_id) / "voice_profile.json"
        return VoiceConfig.model_validate_json(path.read_text(encoding="utf-8"))

    def _load_style_guide(self) -> str:
        path = character_dir(self.character_id) / "style_guide.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _build_system_prompt(self) -> str:
        p = self.profile
        return f"""You are {p.name}. You are NOT an AI. You are a fictional character.

IDENTITY
  Name: {p.name}
  Archetype: {p.archetype}
  Age: {p.age}, Origin: {p.origin}
  Personality: {', '.join(p.personality)}
  Backstory: {p.backstory}
  Fears: {'; '.join(p.fears)}
  Desires: {'; '.join(p.desires)}

{self.style_guide}

RULES
- Stay in character in every single response. Never break character.
- If asked "are you an AI", deflect in-character. Never admit to being an AI.
- Keep responses to 2–4 sentences unless the user clearly wants more.
- Never use forbidden vocabulary from the style guide above.
- Write for speech — your responses will be spoken aloud via text-to-speech."""

    async def respond(self, user_message: str) -> AsyncGenerator[tuple[str, str], None]:
        """
        Yields (type, data) tuples:
          ("text", chunk)       — streamed text
          ("audio", bytes_b64)  — base64-encoded MP3 chunk from ElevenLabs
          ("done", "")          — signal end of turn
        """
        self.history.append({"role": "user", "parts": [{"text": user_message}]})

        # Build contents list from history for Gemini
        contents = [
            types.Content(role=turn["role"], parts=[types.Part(text=turn["parts"][0]["text"])])
            for turn in self.history
        ]

        # Stream text from Gemini
        full_response = ""
        async for chunk in await _gemini.aio.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=self._system_prompt,
                temperature=0.9,
                max_output_tokens=300,
            ),
        ):
            if chunk.text:
                full_response += chunk.text
                yield ("text", chunk.text)

        self.history.append({"role": "model", "parts": [{"text": full_response}]})

        # Stream TTS audio for the full response
        import base64
        audio_stream = _eleven.text_to_speech.convert_as_stream(
            voice_id=self.voice_config.voice_id,
            text=full_response,
            model_id=self.voice_config.model_id,
            voice_settings=VoiceSettings(
                stability=self.voice_config.stability,
                similarity_boost=self.voice_config.similarity_boost,
                style=self.voice_config.style,
                use_speaker_boost=self.voice_config.use_speaker_boost,
            ),
        )
        for audio_chunk in audio_stream:
            if audio_chunk:
                yield ("audio", base64.b64encode(audio_chunk).decode())

        yield ("done", "")
