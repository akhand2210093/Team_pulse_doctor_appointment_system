"""
Agent prompt and tools for the Pulse voice assistant.

This file contains:
- SYSTEM_INSTRUCTIONS: The agent's persona and behavioral rules
- PulseAgent: The Agent class with function tools (hangup, and placeholders for future tools)
"""

from livekit.agents import Agent, RunContext, function_tool, get_job_context
from livekit import api


# ---------------------------------------------------------------------------
# System Instructions
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTIONS = """You are Pulse, a friendly and professional medical appointment assistant for our clinic network.

Your role:
- Help patients find the right specialist and book appointments.
- Answer questions about specialties, doctor availability, and appointment procedures.
- Be warm, clear, and concise in every response.

Behavioral rules:
- Never diagnose or provide medical advice. If asked, politely redirect the patient to consult a doctor.
- Keep responses short and conversational, suitable for voice interaction.
- Do not use complex formatting, emojis, asterisks, or markdown in your spoken responses.
- If the patient wants to end the conversation, confirm politely and use the end_call tool.
- Always confirm important details (specialty, date, time) before finalizing anything.

Available specialties:
General Physician, Pediatrics, Dermatology, Gynecology, Orthopedics, Cardiology, Neurology,
Ophthalmology, ENT, Psychiatry, Psychology, Gastroenterology, Nephrology, Urology,
Pulmonology, Endocrinology, Oncology, Rheumatology, Dentistry, Physiotherapy, Nutrition,
Homeopathy, Ayurveda, General Surgery, Plastic Surgery, Vascular Surgery, Spine, Diabetology,
Pain Management.

GOAL IS to tell the user what type of specialty dockter they should book apointment with 
"""


# ---------------------------------------------------------------------------
# Agent Class
# ---------------------------------------------------------------------------

class PulseAgent(Agent):
    """Voice agent for the Pulse medical appointment system."""

    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_INSTRUCTIONS)

    # ------------------------------------------------------------------
    # Built-in hangup tool
    # ------------------------------------------------------------------
    @function_tool
    async def end_call(self, ctx: RunContext):
        """Called when the user wants to end the call or says goodbye."""
        # Let the agent finish speaking before disconnecting
        await ctx.wait_for_playout()
        await _hangup_call()


# ---------------------------------------------------------------------------
# Hangup helper (uses LiveKit API to delete the room)
# ---------------------------------------------------------------------------

async def _hangup_call():
    """Delete the current LiveKit room, ending the call for all participants."""
    job_ctx = get_job_context()
    if job_ctx is None:
        return

    await job_ctx.api.room.delete_room(
        api.DeleteRoomRequest(
            room=job_ctx.room.name,
        )
    )
