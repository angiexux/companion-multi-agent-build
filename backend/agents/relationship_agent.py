import os
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

from models import CharacterProfile, RelationshipAgentOutput

load_dotenv()

_SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "relationship_system.txt").read_text()
_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def _single_prompt(profile: CharacterProfile) -> str:
    return f"""MODE: single

CharacterProfile A:
Name: {profile.name}
Archetype: {profile.archetype}
Personality: {', '.join(profile.personality)}
Backstory: {profile.backstory}
Fears: {'; '.join(profile.fears)}
Desires: {'; '.join(profile.desires)}

Generate relationship_map_a only. Leave relationship_map_b and relationship_report null."""


def _dual_prompt(a: CharacterProfile, b: CharacterProfile) -> str:
    return f"""MODE: dual

CharacterProfile A:
Name: {a.name}
Archetype: {a.archetype}
Personality: {', '.join(a.personality)}
Backstory: {a.backstory}
Fears: {'; '.join(a.fears)}
Desires: {'; '.join(a.desires)}

CharacterProfile B:
Name: {b.name}
Archetype: {b.archetype}
Personality: {', '.join(b.personality)}
Backstory: {b.backstory}
Fears: {'; '.join(b.fears)}
Desires: {'; '.join(b.desires)}

Generate relationship_map_a, relationship_map_b, and relationship_report."""


async def run_relationship_agent(
    profile_a: CharacterProfile,
    profile_b: CharacterProfile | None = None,
) -> RelationshipAgentOutput:
    prompt = _dual_prompt(profile_a, profile_b) if profile_b else _single_prompt(profile_a)

    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RelationshipAgentOutput,
            temperature=0.8,
        ),
    )
    return RelationshipAgentOutput.model_validate_json(response.text)
