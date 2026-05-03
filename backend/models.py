from pydantic import BaseModel


class VoiceProfile(BaseModel):
    pitch: str
    pace: str
    accent: str
    affect: str


class CharacterProfile(BaseModel):
    id: str
    name: str
    archetype: str
    age: str
    origin: str
    appearance: str
    personality: list[str]
    backstory: str
    fears: list[str]
    desires: list[str]
    speech_era: str
    voice_profile: VoiceProfile
    created_at: str


class RelationshipMap(BaseModel):
    character_id: str
    prey: list[str]
    servants: list[str]
    rivals: list[str]
    equals: list[str]
    fascinations: list[str]
    sworn_enemies: list[str]
    notes: str


class SampleLine(BaseModel):
    speaker: str
    line: str


class RelationshipReport(BaseModel):
    character_a: str
    character_b: str
    dynamic: str
    power_balance: str
    tension_points: list[str]
    interaction_style: str
    sample_exchange: list[SampleLine]


class MemoryEntry(BaseModel):
    character_id: str
    conversation_id: str
    turn_count: int
    summary: str
    emotional_arc: list[str]
    saved_at: str


class CharacterManifest(BaseModel):
    character_id: str
    name: str
    files: dict[str, str]
    consistency_notes: list[dict]
    generated_at: str


class VisualPrompt(BaseModel):
    prompt: str
    negative_prompt: str


class VoiceConfig(BaseModel):
    voice_id: str
    voice_name: str
    model_id: str
    stability: float
    similarity_boost: float
    style: float
    use_speaker_boost: bool
    reasoning: str          # why this voice was chosen — helps debug


class ExampleExchange(BaseModel):
    user: str
    character: str


class DialogueOutput(BaseModel):
    core_principle: str
    patterns: list[str]
    must_use_words: list[str]
    forbidden_words: list[str]
    specialist_terms: list[str]
    emotional_range: dict[str, str]
    example_exchanges: list[ExampleExchange]
    introduction_text: str


class RelationshipAgentOutput(BaseModel):
    relationship_map_a: RelationshipMap
    relationship_map_b: RelationshipMap | None = None
    relationship_report: RelationshipReport | None = None


class ConsistencyNote(BaseModel):
    severity: str   # "warning" | "error"
    field: str      # which artifact had the issue
    message: str


class SynthesisOutput(BaseModel):
    consistent: bool
    notes: list[ConsistencyNote]
    summary: str
