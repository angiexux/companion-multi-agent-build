"""
Pipeline orchestrator — sequences all 6 agents and emits progress events.
Events are sent via an async callback so the caller (WebSocket handler) can
forward them to the client in real time.
"""
import asyncio
import re
from collections.abc import Callable, Awaitable
from datetime import datetime, timezone

from models import CharacterManifest
from agents.lore_agent import run_lore_agent
from agents.dialogue_agent import run_dialogue_agent
from agents.visual_agent import run_visual_agent
from agents.voice_agent import run_voice_agent
from agents.relationship_agent import run_relationship_agent
from agents.synthesis_agent import run_synthesis_agent
from character.manager import (
    save_bio, save_style_guide, save_voice_config, save_manifest,
)

Emit = Callable[[dict], Awaitable[None]]


def _make_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + "_001"


async def run_pipeline(
    prompt: str,
    emit: Emit,
    second_prompt: str | None = None,
) -> CharacterManifest:
    """
    Run the full generation pipeline for one or two characters.
    Calls emit() with typed events throughout so callers can stream progress.
    Returns the manifest for character A (primary).
    """
    dual = second_prompt is not None

    async def _step(agent: str, msg: str):
        await emit({"event": "agent_start", "agent": agent, "message": msg})

    async def _done(agent: str, artifact: str):
        await emit({"event": "agent_complete", "agent": agent, "artifact": artifact})

    # ── Phase 1: Lore ──────────────────────────────────────────────────────
    await _step("LoreAgent", "Building character backstory and profile…")
    if dual:
        profile_a, profile_b = await asyncio.gather(
            run_lore_agent(prompt),
            run_lore_agent(second_prompt),
        )
        save_bio(profile_a)
        save_bio(profile_b)
    else:
        profile_a = await run_lore_agent(prompt)
        profile_b = None
        save_bio(profile_a)
    await _done("LoreAgent", "bio.json")

    # ── Phase 2: Dialogue ──────────────────────────────────────────────────
    await _step("DialogueStyleAgent", "Writing speech patterns and style guide…")
    if dual:
        (dialogue_a, style_md_a), (dialogue_b, style_md_b) = await asyncio.gather(
            run_dialogue_agent(profile_a),
            run_dialogue_agent(profile_b),
        )
        save_style_guide(profile_a.id, style_md_a)
        save_style_guide(profile_b.id, style_md_b)
    else:
        dialogue_a, style_md_a = await run_dialogue_agent(profile_a)
        dialogue_b = None
        save_style_guide(profile_a.id, style_md_a)
    await _done("DialogueStyleAgent", "style_guide.md")

    # ── Phase 3: Visual + Voice (parallel) ────────────────────────────────
    await _step("VisualAgent", "Generating portrait…")
    await _step("VoiceAgent", "Synthesising voice sample…")

    if dual:
        results = await asyncio.gather(
            run_visual_agent(profile_a),
            run_visual_agent(profile_b),
            run_voice_agent(profile_a, dialogue_a),
            run_voice_agent(profile_b, dialogue_b),
        )
        (visual_prompt_a, _), (visual_prompt_b, _) = results[0], results[1]
        (voice_config_a, _), (voice_config_b, _) = results[2], results[3]
        save_voice_config(profile_a.id, voice_config_a)
        save_voice_config(profile_b.id, voice_config_b)
    else:
        (visual_prompt_a, _), (voice_config_a, _) = await asyncio.gather(
            run_visual_agent(profile_a),
            run_voice_agent(profile_a, dialogue_a),
        )
        visual_prompt_b = voice_config_b = None
        save_voice_config(profile_a.id, voice_config_a)

    await _done("VisualAgent", "portrait.png")
    await _done("VoiceAgent", "voice_sample.mp3")

    # ── Phase 4: Relationship ──────────────────────────────────────────────
    await _step("RelationshipDynamicsAgent", "Mapping relationships…")
    rel_output = await run_relationship_agent(profile_a, profile_b)

    rel_map_a = rel_output.relationship_map_a
    from character.manager import character_dir
    import json

    (character_dir(profile_a.id) / "relationship_map.json").write_text(
        rel_map_a.model_dump_json(indent=2), encoding="utf-8"
    )
    if dual and rel_output.relationship_map_b and rel_output.relationship_report:
        (character_dir(profile_b.id) / "relationship_map.json").write_text(
            rel_output.relationship_map_b.model_dump_json(indent=2), encoding="utf-8"
        )
        (character_dir(profile_a.id) / "relationship_report.json").write_text(
            rel_output.relationship_report.model_dump_json(indent=2), encoding="utf-8"
        )
    await _done("RelationshipDynamicsAgent", "relationship_map.json")

    # ── Phase 5: Synthesis ─────────────────────────────────────────────────
    await _step("SynthesisAgent", "Checking consistency across all artifacts…")
    synthesis = await run_synthesis_agent(
        profile_a, visual_prompt_a, voice_config_a, dialogue_a, rel_map_a
    )
    await _done("SynthesisAgent", "manifest.json")

    # ── Build manifest ─────────────────────────────────────────────────────
    files = {
        "bio": f"characters/{profile_a.id}/bio.json",
        "portrait": f"characters/{profile_a.id}/portrait.png",
        "voice_sample": f"characters/{profile_a.id}/voice_sample.mp3",
        "style_guide": f"characters/{profile_a.id}/style_guide.md",
        "relationship_map": f"characters/{profile_a.id}/relationship_map.json",
    }
    if dual:
        files["relationship_report"] = f"characters/{profile_a.id}/relationship_report.json"

    manifest = CharacterManifest(
        character_id=profile_a.id,
        name=profile_a.name,
        files=files,
        consistency_notes=[n.model_dump() for n in synthesis.notes],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    save_manifest(manifest)

    await emit({
        "event": "generation_complete",
        "character_id": profile_a.id,
        "name": profile_a.name,
        "consistent": synthesis.consistent,
    })

    return manifest
