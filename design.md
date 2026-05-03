# Companion Multi-Agent Build — Technical Design

## System Architecture

```
                        ┌─────────────────────────────────┐
                        │           FRONTEND               │
                        │   React + Vite                   │
                        │   - Input form                   │
                        │   - Per-agent progress strip     │
                        │   - Character card display       │
                        │   - Companion chat panel         │
                        │   - Audio player (TTS stream)    │
                        └──────────────┬──────────────────┘
                                       │ HTTP + WebSocket
                        ┌──────────────▼──────────────────┐
                        │           BACKEND                │
                        │   FastAPI                        │
                        │   POST /generate                 │
                        │   POST /activate                 │
                        │   WS  /ws/generate/{job_id}      │
                        │   WS  /ws/companion/{char_id}    │
                        └──────────────┬──────────────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │        ORCHESTRATOR              │
                        │   AG2 GroupChat                  │
                        │   AutoPattern speaker selection  │
                        └──┬───┬───┬───┬───┬──────────────┘
                           │   │   │   │   │
              ┌────────────┘   │   │   │   └──────────────┐
              │         ┌──────┘   │   └──────┐           │
              ▼         ▼          ▼          ▼           ▼
         LoreAgent VisualAgent VoiceAgent DialogueAgent RelationshipAgent
         (Gemini)  (Gemini     (ElevenLabs (Gemini     (Gemini → runs
                   → FAL.ai)   API)        Flash)       second pipeline
                                                         if dual mode)
              │         │          │          │           │
              └─────────┴──────────┴──────────┴───────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │        SynthesisAgent            │
                        │   Validates consistency          │
                        │   Assembles final package        │
                        └──────────────┬──────────────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │      characters/<id>/            │
                        │   bio.json                       │
                        │   portrait.png                   │
                        │   voice_sample.mp3               │
                        │   style_guide.md                 │
                        │   relationship_map.json          │
                        └─────────────────────────────────┘
```

---

## Tech Stack

| Layer | Choice | Version | Notes |
|---|---|---|---|
| Agent orchestration | AG2 | latest | GroupChat + AutoPattern, no custom orchestration |
| LLM | Gemini 2.0 Flash | gemini-2.0-flash | Via `google-generativeai` SDK |
| Image generation | FAL.ai (Flux) | fal-client | Flux-dev or Flux-schnell for speed |
| Voice synthesis | ElevenLabs | elevenlabs SDK | TTS + streaming for companion mode |
| Backend | FastAPI | 0.115+ | Async WebSocket support |
| Frontend | React + Vite | React 18, Vite 5 | Tailwind for styling |
| Storage | JSON files | — | `characters/` directory, no database |
| State (frontend) | Zustand | 5.x | Lightweight, no Redux overhead |

---

## Agent Roster

### OrchestratorAgent

**Role:** AG2 GroupChat manager. Parses input, detects single vs. dual character, sequences agents, passes context via `ContextVariables`.

**System prompt excerpt:**
```
You are the orchestrator for a character creation pipeline. Your job is to:
1. Parse the user's description and extract character concepts
2. If you detect "vs", "and", or two named characters, run dual-character mode
3. Sequence specialist agents in order: Lore → Visual + Voice (parallel) → Dialogue → Relationship → Synthesis
4. Pass each agent's output as context to subsequent agents
5. Never generate character content yourself — delegate to specialists
```

**ContextVariables schema:**
```python
{
    "raw_prompt": str,
    "mode": "single" | "dual",
    "character_a_prompt": str,
    "character_b_prompt": str | None,
    "bio_a": dict | None,        # filled by LoreAgent
    "bio_b": dict | None,
    "portrait_path_a": str | None,  # filled by VisualAgent
    "voice_path_a": str | None,     # filled by VoiceAgent
    "style_guide_a": str | None,    # filled by DialogueAgent
    "relationship_map_a": dict | None,  # filled by RelationshipAgent
    "relationship_report": dict | None,  # dual mode only
    "synthesis_result": dict | None,
}
```

---

### LoreAgent

**Role:** Transforms free-text prompt into structured `bio.json`. This is the foundation all other agents build on.

**Input:** `raw_prompt` (string)

**Output:** `bio.json` (CharacterProfile schema, see below)

**System prompt:** Instruct Gemini to output valid JSON matching CharacterProfile. Include examples. Force detailed backstory (3+ sentences), specific fears/desires (not generic), and a `voice_profile` sub-object that other agents will use.

**Implementation:**
```python
# agents/lore_agent.py
import autogen
from google.generativeai import GenerativeModel

lore_agent = autogen.AssistantAgent(
    name="LoreAgent",
    system_message=LORE_SYSTEM_PROMPT,
    llm_config={"model": "gemini-2.0-flash", ...}
)
```

---

### VisualAgent

**Role:** Writes a detailed image generation prompt from `bio.json`, then calls FAL.ai to generate the portrait.

**Input:** `bio.json`

**Output:** `portrait.png` (saved to `characters/<id>/portrait.png`), path returned

**Two-step process:**
1. Gemini reads `bio.json` → writes optimized Flux prompt (appearance, setting, lighting, style)
2. FAL.ai Flux API call with that prompt

**FAL.ai call:**
```python
import fal_client

result = fal_client.subscribe(
    "fal-ai/flux/dev",
    arguments={
        "prompt": image_prompt,
        "image_size": "square_hd",
        "num_images": 1,
        "num_inference_steps": 28,
    }
)
image_url = result["images"][0]["url"]
```

**Prompt engineering notes:**
- Force "portrait" framing to avoid full-body shots
- Include "cinematic lighting" to avoid flat AI look
- Negative prompt: "multiple people, crowd, anime, cartoon, deformed"

---

### VoiceAgent

**Role:** Maps `bio.json` voice_profile to ElevenLabs settings, generates a 10–15 second character introduction, returns MP3.

**Input:** `bio.json` (specifically `voice_profile` + `personality` + first line of `backstory`)

**Output:** `voice_sample.mp3`

**Voice selection strategy:**
- Deep + slow + formal → preset "Adam" or "Antoni" (ElevenLabs preset IDs)
- High + fast + nervous → "Rachel" 
- Raspy + age-worn → "Arnold"
- The DialogueAgent writes the intro text; VoiceAgent calls ElevenLabs with it

**ElevenLabs call:**
```python
from elevenlabs import ElevenLabs, VoiceSettings

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

audio = client.text_to_speech.convert(
    voice_id=selected_voice_id,
    text=intro_text,
    model_id="eleven_turbo_v2_5",
    voice_settings=VoiceSettings(
        stability=0.85,
        similarity_boost=0.75,
        style=0.3,
    )
)
```

**For companion mode (streaming):**
```python
audio_stream = client.text_to_speech.convert_as_stream(
    voice_id=selected_voice_id,
    text=response_text,
    model_id="eleven_turbo_v2_5",
)
# Yield chunks over WebSocket
```

---

### DialogueStyleAgent

**Role:** Creates `style_guide.md` — the behavioral contract the companion follows in activation mode.

**Input:** `bio.json`

**Output:** `style_guide.md` (markdown string, saved to file)

**Required sections in style guide:**
1. Core principle (1–2 sentences on the character's fundamental speech philosophy)
2. Patterns (3–5 recurring constructions)
3. Vocabulary (must-use words, forbidden words, archaic or specialist terms)
4. Emotional range (how the character expresses each emotion)
5. Example exchanges (3 Q&A pairs that demonstrate the style)

**Also generates:** The 10–15 second intro text that VoiceAgent will synthesize. Passed via ContextVariables.

---

### RelationshipDynamicsAgent

**Role:** 
- Single mode: generates `relationship_map.json` for the character
- Dual mode: receives both `bio.json` files, generates both `relationship_map.json` files AND `relationship_report.json`

**Input (single):** `bio.json`
**Input (dual):** `bio_a.json` + `bio_b.json`

**Output:** 
- `relationship_map.json` (per character)
- `relationship_report.json` (dual mode only)

**Dual mode trigger:**
```python
if context_vars["mode"] == "dual":
    # Run full second pipeline for character_b first
    # Then call RelationshipDynamicsAgent with both bios
```

---

### SynthesisAgent

**Role:** Reads all generated artifacts, checks for consistency, flags issues, assembles final manifest.

**Input:** All 5 artifacts for each character

**Output:** `manifest.json` (paths, timestamps, consistency notes)

**Consistency checks:**
- Portrait prompt mentions same appearance details as `bio.json`
- Voice settings match `voice_profile` in `bio.json`
- Style guide vocabulary doesn't contradict personality traits
- Relationship map mentions are internally consistent

**If inconsistency detected:** Flags it in manifest with severity (warning / error). Does NOT re-run agents (hackathon speed > perfection).

---

## Data Schemas

### CharacterProfile (`bio.json`)

```typescript
interface CharacterProfile {
  id: string;                    // e.g. "dracula_001"
  name: string;
  archetype: string;             // e.g. "ancient predator"
  age: string;                   // string to allow "500+" or "unknown"
  origin: string;                // place + approximate era
  appearance: string;            // paragraph for portrait generation
  personality: string[];         // 4–8 trait words
  backstory: string;             // 3+ sentence narrative
  fears: string[];               // 3–5 specific fears
  desires: string[];             // 3–5 specific desires
  speech_era: string;            // e.g. "Victorian formal", "contemporary street"
  voice_profile: {
    pitch: string;               // "deep baritone" | "tenor" | "alto" etc.
    pace: string;                // "deliberate" | "rapid" | "staccato"
    accent: string;              // nationality/region
    affect: string;              // emotional register
  };
  created_at: string;            // ISO 8601
}
```

### RelationshipMap (`relationship_map.json`)

```typescript
interface RelationshipMap {
  character_id: string;
  prey: string[];
  servants: string[];
  rivals: string[];
  equals: string[];
  fascinations: string[];
  sworn_enemies: string[];
  notes: string;
}
```

### RelationshipReport (`relationship_report.json`)

```typescript
interface RelationshipReport {
  character_a: string;           // character_id
  character_b: string;
  dynamic: string;               // one-phrase summary
  power_balance: string;
  tension_points: string[];
  interaction_style: string;
  sample_exchange: Array<{ [character_name: string]: string }>;
}
```

### MemoryEntry (`memories/<char_id>/<conv_id>.json`)

```typescript
interface MemoryEntry {
  character_id: string;
  conversation_id: string;
  turn_count: number;
  summary: string;
  emotional_arc: string[];
  saved_at: string;
}
```

### Manifest (`manifest.json`)

```typescript
interface CharacterManifest {
  character_id: string;
  name: string;
  files: {
    bio: string;
    portrait: string;
    voice_sample: string;
    style_guide: string;
    relationship_map: string;
  };
  consistency_notes: Array<{
    severity: "warning" | "error";
    message: string;
  }>;
  generated_at: string;
}
```

---

## API Surface

### REST

```
POST /generate
  Body: { prompt: string }
  Response: { job_id: string }

POST /activate
  Body: { character_id: string }
  Response: { session_id: string }

GET /characters
  Response: CharacterManifest[]

GET /characters/{character_id}
  Response: CharacterManifest

GET /characters/{character_id}/portrait
  Response: image/png

GET /characters/{character_id}/voice
  Response: audio/mpeg
```

### WebSocket

```
WS /ws/generate/{job_id}
  Server → Client events:
    { event: "agent_start",    agent: string, message: string }
    { event: "agent_complete", agent: string, artifact: string }
    { event: "generation_complete", character_id: string }
    { event: "error", agent: string, message: string }

WS /ws/companion/{session_id}
  Client → Server:
    { type: "user_message", text: string }
  Server → Client:
    { type: "text_chunk",  text: string }
    { type: "audio_chunk", data: base64_pcm }
    { type: "response_complete" }
```

---

## File Structure

```
companion-multi-agent-build/
├── spec.md
├── design.md
├── README.md
├── .env.example
│
├── backend/
│   ├── main.py                     ← FastAPI app, routes, WebSocket handlers
│   ├── requirements.txt
│   │
│   ├── agents/
│   │   ├── orchestrator.py         ← AG2 GroupChat setup, ContextVariables
│   │   ├── lore_agent.py
│   │   ├── visual_agent.py
│   │   ├── voice_agent.py
│   │   ├── dialogue_agent.py
│   │   ├── relationship_agent.py
│   │   └── synthesis_agent.py
│   │
│   ├── tools/
│   │   ├── fal_tools.py            ← generate_portrait(prompt) → path
│   │   └── elevenlabs_tools.py     ← generate_voice_sample(text, settings) → path
│   │                               ← stream_tts(text, settings) → generator
│   │
│   ├── character/
│   │   ├── manager.py              ← save_character(), load_character(), list_characters()
│   │   └── companion.py            ← CompanionSession: chat loop, memory, TTS streaming
│   │
│   └── prompts/
│       ├── lore_system.txt
│       ├── visual_system.txt
│       ├── voice_system.txt
│       ├── dialogue_system.txt
│       ├── relationship_system.txt
│       └── synthesis_system.txt
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── InputForm.tsx       ← prompt input + generate button
│   │   │   ├── GenerationProgress.tsx ← per-agent progress strip
│   │   │   ├── CharacterCard.tsx   ← portrait + bio + voice player
│   │   │   ├── StyleGuidePanel.tsx ← style guide display
│   │   │   ├── RelationshipMap.tsx ← relationship map visualization
│   │   │   └── CompanionChat.tsx   ← chat interface + TTS playback
│   │   └── stores/
│   │       ├── generationStore.ts  ← job status, agent progress
│   │       └── companionStore.ts   ← active session, messages, audio queue
│
└── characters/                     ← Generated character packages
    ├── dracula_001/
    │   ├── bio.json
    │   ├── portrait.png
    │   ├── voice_sample.mp3
    │   ├── style_guide.md
    │   ├── relationship_map.json
    │   └── manifest.json
    └── van_helsing_001/
        └── ...
```

---

## AG2 GroupChat Setup

```python
# agents/orchestrator.py
import autogen

def create_pipeline(context_vars: dict) -> autogen.GroupChat:
    lore = LoreAgent()
    visual = VisualAgent()
    voice = VoiceAgent()
    dialogue = DialogueStyleAgent()
    relationship = RelationshipDynamicsAgent()
    synthesis = SynthesisAgent()
    
    user_proxy = autogen.UserProxyAgent(
        name="Orchestrator",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=20,
        code_execution_config=False,
    )
    
    groupchat = autogen.GroupChat(
        agents=[user_proxy, lore, visual, voice, dialogue, relationship, synthesis],
        messages=[],
        max_round=15,
        speaker_selection_method="auto",  # AutoPattern — AG2 selects next speaker
    )
    
    manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=GEMINI_CONFIG,
    )
    
    return user_proxy, manager
```

**Execution order enforced via system prompts:** Each agent's system prompt begins with "You speak ONLY when the previous agent has completed their output and your specific artifact has not yet been created." This guides AG2's AutoPattern speaker selection without custom orchestration logic.

---

## Companion Session Architecture

```python
# character/companion.py
class CompanionSession:
    def __init__(self, character_id: str):
        self.bio = load_character(character_id)["bio"]
        self.style_guide = load_character(character_id)["style_guide"]
        self.memory: list[MemoryEntry] = []
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        return f"""
You are {self.bio['name']}. You are NOT an AI assistant.
You respond ONLY in-character, following this style guide exactly:

{self.style_guide}

Your backstory: {self.bio['backstory']}
Your fears: {', '.join(self.bio['fears'])}
Your desires: {', '.join(self.bio['desires'])}

Previous session memory:
{self._format_memory()}

Never break character. Never acknowledge being an AI. Never use forbidden vocabulary.
"""
    
    async def respond(self, user_message: str) -> AsyncGenerator[str, None]:
        # Gemini streaming response
        # Yield text chunks → also pipe to ElevenLabs TTS stream
        ...
    
    async def save_memory(self):
        # Summarize conversation, save MemoryEntry
        ...
```

---

## Environment Variables

```bash
# .env.example
GOOGLE_API_KEY=                 # Gemini 2.0 Flash
FAL_KEY=                        # FAL.ai (Flux image generation)
ELEVENLABS_API_KEY=             # ElevenLabs TTS
CHARACTERS_DIR=./characters     # Output directory
```

---

## Implementation Sequence

1. **Scaffold** — FastAPI server boots, `/generate` endpoint accepts prompt, returns job_id
2. **LoreAgent** — Prompt → bio.json working end-to-end
3. **DialogueStyleAgent** — bio.json → style_guide.md (text only, no external APIs)
4. **VisualAgent** — bio.json → FAL.ai call → portrait.png
5. **VoiceAgent** — style_guide intro text → ElevenLabs → voice_sample.mp3
6. **RelationshipAgent** — bio.json → relationship_map.json; dual mode adds relationship_report.json
7. **SynthesisAgent** — All artifacts → manifest.json
8. **WebSocket progress events** — Each agent emits `agent_start` + `agent_complete` over WS
9. **Companion mode** — CompanionSession: chat loop + ElevenLabs TTS streaming
10. **Frontend** — React app: input → progress strip → character card → companion chat

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| FAL.ai rate limits / slow | Cache one pre-generated Dracula portrait as fallback |
| ElevenLabs free tier quota | Pre-generate voice samples for demo characters |
| AG2 speaker selection loops | Hard cap at 15 rounds; synthesis agent has "TERMINATE" trigger |
| Gemini JSON output malformed | Parse with `json.loads` inside try/except; retry once with stricter prompt |
| ElevenLabs TTS latency in companion mode | Stream audio chunks as they arrive; don't wait for full response |
| Dual character pipeline slow | Run both character pipelines with `asyncio.gather()` |
