"""
LiveKit Agent Worker for Pulse.

Run separately with:
    uv run agent_worker.py dev

This worker registers as 'pulse-agent' with the LiveKit server.
It uses Gemini's native audio model for real-time voice conversations.
"""

from dotenv import load_dotenv

load_dotenv()

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, room_io
from livekit.plugins import google
from google.genai import types

from agent_prompt import PulseAgent


# ---------------------------------------------------------------------------
# Agent Server & Session
# ---------------------------------------------------------------------------

server = AgentServer()


@server.rtc_session(agent_name="pulse-agent")
async def entrypoint(ctx: agents.JobContext):
    """Handle an incoming voice session dispatched to 'pulse-agent'."""

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Kore",
            temperature=0.7,
            enable_affective_dialog=True,
            proactivity=True,
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
            ),
        ),
    )

    await session.start(
        room=ctx.room,
        agent=PulseAgent(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    None  # Skip noise cancellation for simplicity; can add BVC later
                ),
            ),
        ),
    )

    # Greet the user once connected
    await session.generate_reply(
        instructions="Greet the patient warmly. Introduce yourself as Pulse, the clinic assistant. Ask how you can help them today."
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agents.cli.run_app(server)
