# Companion Multi-Agent Build

Multi-agent AI system that generates rich character packages from a text description, then activates them as live conversational companions.

## Stack
- **Agents:** AG2 (GroupChat + AutoPattern)
- **LLM:** Gemini 2.0 Flash
- **Image gen:** FAL.ai (Flux)
- **Voice:** ElevenLabs
- **Backend:** FastAPI + WebSocket
- **Frontend:** React + Vite

## Docs
- [spec.md](spec.md) — Product requirements with Dracula worked example
- [design.md](design.md) — Full technical architecture and agent contracts

## Setup
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in API keys
python test_lore.py          # smoke test: generates Dracula bio.json
```

## Example
Input: `"Count Dracula — ancient Romanian vampire lord, aristocratic and predatory"`

Output: `bio.json` + `portrait.png` + `voice_sample.mp3` + `style_guide.md` + `relationship_map.json`
