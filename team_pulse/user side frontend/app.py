"""
Pulse — FastAPI + Gradio app.
Home page: agent chat bar (text + voice) + specialty grid.
Booking page: doctor search with real API slots.
"""

import os
import uuid
import httpx

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import gradio as gr

from google import genai
from google.genai import types as genai_types
from livekit.api import AccessToken, RoomAgentDispatch, RoomConfiguration, VideoGrants
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
USE_DUMMY_DATA = os.environ.get("USE_DUMMY_DATA", "false").lower() == "true"

TEXT_MODEL = "gemini-2.5-flash-lite"
AGENT_NAME = "pulse-agent"
BACKEND_URL = "https://hcl-das-backend.onrender.com/api"

gemini_client = genai.Client(api_key=GOOGLE_API_KEY)

# ---------------------------------------------------------------------------
# Backend API helpers  (Render free tier cold-starts can take 30-60s!)
# ---------------------------------------------------------------------------
import time as _time

_api_cache: dict[str, tuple[float, any]] = {}   # path -> (timestamp, data)
CACHE_TTL = 300  # 5 minutes

async def api_get(path: str, params: dict = None, use_cache: bool = True):
    """GET from Django backend with cache + generous timeout."""
    cache_key = f"{path}:{params}"
    if use_cache and cache_key in _api_cache:
        ts, data = _api_cache[cache_key]
        if _time.time() - ts < CACHE_TTL:
            return data

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{BACKEND_URL}{path}", params=params)
        r.raise_for_status()
        data = r.json()
        _api_cache[cache_key] = (_time.time(), data)
        return data

async def api_post(path: str, data: dict):
    """POST to Django backend."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{BACKEND_URL}{path}", json=data)
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Fetch specialties from backend (cached)
# ---------------------------------------------------------------------------
_specialties_cache = None

async def get_specialties_list():
    """Fetch specialties from backend, cache result."""
    global _specialties_cache
    if _specialties_cache is not None:
        return _specialties_cache
    try:
        data = await api_get("/specialties/")
        _specialties_cache = data  # list of {id, name}
        return data
    except Exception:
        return []

def get_specialty_names():
    """Synchronous access to cached specialty names for Gradio UI."""
    if _specialties_cache:
        return [s["name"] for s in _specialties_cache]
    # Fallback list in case cache isn't populated yet
    return [
        "General Physician", "Pediatrics", "Dermatology", "Gynecology",
        "Orthopedics", "Cardiology", "Neurology", "Ophthalmology",
        "ENT", "Psychiatry", "Psychology", "Gastroenterology",
        "Nephrology", "Urology", "Pulmonology", "Endocrinology",
        "Oncology", "Rheumatology", "Dentistry", "Physiotherapy",
        "Nutrition", "Homeopathy", "Ayurveda", "General Surgery",
        "Plastic Surgery", "Vascular Surgery", "Spine", "Diabetology",
        "Pain Management",
    ]


CHAT_SYSTEM = (
    "You are Pulse, a friendly medical appointment assistant. "
    "Help patients find specialists, book appointments, and answer questions. "
    "Be concise. Never diagnose or give medical advice. "
    "If asked about booking, guide them to use the booking section below the chat."
)


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(title="Pulse")

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
async def on_startup():
    """Pre-load specialties cache on startup."""
    await get_specialties_list()


@app.post("/api/voice/token")
async def voice_token(user_id: str = ""):
    room_name = f"pulse-{uuid.uuid4().hex[:8]}"
    identity = user_id if user_id else f"patient-{uuid.uuid4().hex[:6]}"
    token = (
        AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .with_room_config(RoomConfiguration(agents=[RoomAgentDispatch(agent_name=AGENT_NAME)]))
        .to_jwt()
    )
    return JSONResponse({"token": token, "url": LIVEKIT_URL, "room_name": room_name})


@app.get("/api/specialties")
async def get_specialties_endpoint():
    data = await get_specialties_list()
    return JSONResponse({"specialties": data})


@app.get("/api/doctors")
async def get_doctors(specialty: str = "", mode: str = "online"):
    """Fetch doctors from backend, filter by specialty name and mode."""
    try:
        all_doctors = await api_get("/doctors/")
        specs = await get_specialties_list()
        spec_map = {s["id"]: s["name"] for s in specs}

        filtered = []
        for d in all_doctors:
            if not d.get("active", True):
                continue
            doc_spec = spec_map.get(d["specialty"], "")
            if specialty and doc_spec.lower() != specialty.lower():
                continue
            if mode and d.get("mode", "").lower() != mode.lower():
                continue
            d["specialty_name"] = doc_spec
            filtered.append(d)
        return JSONResponse({"doctors": filtered})
    except Exception as e:
        return JSONResponse({"doctors": [], "error": str(e)})


from pydantic import BaseModel

class BookingRequest(BaseModel):
    patient_name: str
    patient_contact: str
    patient_dob: str        # YYYY-MM-DD
    patient_email: str
    doctor_id: int
    schedule_id: int
    mode: str               # online / offline
    fee: str                # decimal string
    user_id: str = ""       # carried from URL

@app.post("/api/book")
async def book_appointment(req: BookingRequest):
    """Create patient + appointment in one call."""
    try:
        # 1. Create patient
        patient = await api_post("/patients/", {
            "name": req.patient_name,
            "contact": req.patient_contact,
            "dob": req.patient_dob,
            "email": req.patient_email,
        })
        patient_id = patient["id"]

        # 2. Create appointment
        appointment = await api_post("/appointments/", {
            "patient": patient_id,
            "doctor": req.doctor_id,
            "schedule": req.schedule_id,
            "mode": req.mode,
            "fee": req.fee,
            "status": "confirmed",
        })

        return JSONResponse({
            "success": True,
            "appointment_id": appointment["id"],
            "patient_id": patient_id,
            "message": f"Appointment confirmed! ID: {appointment['id']}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.get("/api/slots")
async def get_slots(doctor_id: str = "", date: str = ""):
    """Fetch available (not booked) schedule slots for a doctor on a date."""
    try:
        all_schedules = await api_get("/schedules/")
        slots = [
            s for s in all_schedules
            if str(s["doctor"]) == str(doctor_id)
            and s["date"] == date
            and not s["is_booked"]
        ]
        return JSONResponse({"slots": slots})
    except Exception as e:
        return JSONResponse({"slots": [], "error": str(e)})


@app.post("/api/appointments")
async def create_appointment_endpoint(
    patient_name: str = "",
    patient_email: str = "",
    patient_contact: str = "",
    patient_dob: str = "",
    doctor_id: int = 0,
    schedule_id: int = 0,
    mode: str = "online",
    fee: str = "0",
):
    """Create patient (if not exists) and book appointment."""
    try:
        # 1. Create or find patient
        patient = await api_post("/patients/", {
            "name": patient_name,
            "email": patient_email,
            "contact": patient_contact,
            "dob": patient_dob,
        })
        patient_id = patient["id"]

        # 2. Create appointment
        appointment = await api_post("/appointments/", {
            "patient": patient_id,
            "doctor": doctor_id,
            "schedule": schedule_id,
            "mode": mode,
            "fee": fee,
        })
        return JSONResponse({"status": "confirmed", "appointment": appointment})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


# ---------------------------------------------------------------------------
# Read CSS
# ---------------------------------------------------------------------------
css_path = static_dir / "style.css"
custom_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""


# ---------------------------------------------------------------------------
# Gradio — Home Page
# ---------------------------------------------------------------------------

def _specialty_grid_html(user_id=""):
    names = get_specialty_names()
    uid_param = f"&user_id={user_id}" if user_id else ""
    cards = "".join(
        f'<a class="spec-card" href="/booking/?specialty={s.replace(" ", "+")}{uid_param}">{s}</a>\n'
        for s in names
    )
    return f'<div class="spec-grid">{cards}</div>'


def _home():
    with gr.Blocks(title="Pulse — Your Health Companion") as demo:
        gr.HTML(f"<style>{custom_css}</style>")

        gr.HTML('<div class="greeting"><h1>Welcome to Pulse</h1><p>Your trusted health companion</p></div>')

        # --- User ID state (read from URL) ---
        user_id_state = gr.State("")

        # --- Agent bar ---
        agent_expanded = gr.State(False)

        with gr.Group(elem_id="agent-box"):
            expand_btn = gr.Button(
                "✨ Talk to Pulse — Ask anything about appointments",
                elem_id="agent-bar-btn", variant="secondary",
            )

            with gr.Column(visible=False, elem_id="chat-area") as chat_col:
                chatbot = gr.Chatbot(height=340, elem_id="chatbot")

                chat_input = gr.MultimodalTextbox(
                    placeholder="Type a message or attach a file...",
                    show_label=False,
                    file_count="multiple",
                    file_types=["image", ".pdf", ".doc", ".docx"],
                    elem_id="chat-input",
                    sources=["upload"],
                )

                with gr.Row(elem_id="voice-row"):
                    mic_btn = gr.Button("Start Voice Call", elem_id="mic-btn", variant="secondary", scale=1)
                    voice_status = gr.HTML('<span id="voice-status"></span>')

        def toggle_chat(expanded):
            return not expanded, gr.Column(visible=not expanded)

        expand_btn.click(toggle_chat, agent_expanded, [agent_expanded, chat_col])

        # --- Text chat (fixed: pass user_msg explicitly via State) ---
        last_user_text = gr.State("")

        def add_message(history, message):
            if history is None:
                history = []

            user_text = ""
            files = message.get("files", []) if isinstance(message, dict) else []
            text = message.get("text", "") if isinstance(message, dict) else str(message)

            for f in files:
                history.append({"role": "user", "content": {"path": f}})
            if text:
                history.append({"role": "user", "content": text})
                user_text = text

            return history, gr.MultimodalTextbox(value=None, interactive=False), user_text

        def bot_respond(history, user_text):
            if not user_text:
                return history

            # Build full conversation history for Gemini
            gemini_contents = []
            for msg in history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                # Skip file/media entries, only send text
                if not isinstance(content, str) or not content.strip():
                    continue
                # Gemini uses "user" and "model" roles
                gemini_role = "model" if role == "assistant" else "user"
                gemini_contents.append(
                    genai_types.Content(role=gemini_role, parts=[genai_types.Part.from_text(text=content)])
                )

            # If somehow history didn't capture the current message, add it
            if not gemini_contents or gemini_contents[-1].role != "user":
                gemini_contents.append(
                    genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=user_text)])
                )

            history.append({"role": "assistant", "content": ""})
            try:
                resp = gemini_client.models.generate_content_stream(
                    model=TEXT_MODEL,
                    contents=gemini_contents,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=CHAT_SYSTEM, temperature=0.7, max_output_tokens=1024,
                    ),
                )
                for chunk in resp:
                    if chunk.text:
                        history[-1]["content"] += chunk.text
                        yield history
            except Exception as e:
                history[-1]["content"] = f"Sorry, something went wrong: {e}"
                yield history

        chat_input.submit(
            add_message, [chatbot, chat_input], [chatbot, chat_input, last_user_text]
        ).then(
            bot_respond, [chatbot, last_user_text], chatbot
        ).then(
            lambda: gr.MultimodalTextbox(interactive=True), None, [chat_input]
        )

        # --- Specialty grid ---
        gr.HTML('<div class="book-heading"><h2>Book an Appointment</h2><p>Select a specialty to find available doctors</p></div>')
        spec_grid_html = gr.HTML(_specialty_grid_html())
        gr.HTML('<div class="footer">Pulse Health — Trusted care, always accessible</div>')

        # --- Load user_id from URL and update specialty grid links ---
        def load_user_id(request: gr.Request):
            params = dict(request.query_params) if request else {}
            uid = params.get("user_id", "")
            return uid, _specialty_grid_html(uid)

        demo.load(load_user_id, None, [user_id_state, spec_grid_html])

        # --- LiveKit JS ---
        gr.HTML("""
        <script src="https://cdn.jsdelivr.net/npm/livekit-client/dist/livekit-client.umd.min.js"></script>
        <script>
        (function() {
            let room = null, isConnected = false;
            function setS(t,c){const st=document.getElementById('voice-status');if(st)st.innerHTML=t?'<span class="voice-tag '+(c||'')+'">'+t+'</span>':'';}

            function attachMicHandler() {
                const btn = document.getElementById('mic-btn');
                if (!btn) return;
                // Prevent double-binding
                if (btn._lkBound) return;
                btn._lkBound = true;

                btn.addEventListener('click', async()=>{
                    if(isConnected){
                        if(room){room.disconnect();room=null;}
                        isConnected=false; btn.textContent='Start Voice Call'; btn.classList.remove('voice-active'); setS('');
                        return;
                    }
                    btn.textContent='Connecting...'; setS('Connecting...','connecting');
                    try{
                        const r=await fetch('/api/voice/token?user_id=' + encodeURIComponent(window._pulseUserId || ''),{method:'POST'});
                        const d=await r.json();
                        room=new LivekitClient.Room({adaptiveStream:true,dynacast:true});
                        room.on(LivekitClient.RoomEvent.TrackSubscribed,(track)=>{
                            if(track.kind===LivekitClient.Track.Kind.Audio){const el=track.attach();el.style.display='none';document.body.appendChild(el);}
                        });
                        room.on(LivekitClient.RoomEvent.TrackUnsubscribed,(track)=>{track.detach().forEach(e=>e.remove());});
                        room.on(LivekitClient.RoomEvent.Disconnected,()=>{isConnected=false;btn.textContent='Start Voice Call';btn.classList.remove('voice-active');setS('Call ended','ended');setTimeout(()=>setS(''),3000);});
                        room.on(LivekitClient.RoomEvent.ParticipantConnected,()=>{setS('Agent connected — speak now','live');});
                        await room.connect(d.url,d.token);
                        await room.localParticipant.setMicrophoneEnabled(true);
                        isConnected=true; btn.textContent='End Call'; btn.classList.add('voice-active'); setS('Waiting for agent...','waiting');
                    }catch(e){console.error('Voice error:',e);btn.textContent='Start Voice Call';setS('Connection failed','error');setTimeout(()=>setS(''),4000);}
                });
                console.log('[Pulse] Voice call handler attached');
            }

            // Poll for the button (Gradio renders dynamically)
            const poll = setInterval(()=>{
                if(document.getElementById('mic-btn')){attachMicHandler();clearInterval(poll);}
            }, 500);
            // Also try immediately
            attachMicHandler();
        })();
        </script>
        <script>
          // Extract user_id from URL for JS use
          (function(){
            const p = new URLSearchParams(window.location.search);
            window._pulseUserId = p.get('user_id') || '';
          })();
        </script>
        """)

    return demo


# ---------------------------------------------------------------------------
# Gradio — Booking Page (wired to real API)
# ---------------------------------------------------------------------------

def _booking():
    with gr.Blocks(title="Book Appointment — Pulse") as demo:
        gr.HTML(f"<style>{custom_css}</style>")

        gr.HTML('<div class="booking-top"><a href="/" class="back-link">&larr; Back</a><h1>Book an Appointment</h1></div>')

        with gr.Row():
            with gr.Column(scale=1):
                specialty_dd = gr.Dropdown(
                    choices=get_specialty_names(),
                    label="Specialty", elem_id="spec-dd", interactive=True,
                )
                mode_dd = gr.Radio(["Online", "Offline"], value="Online", label="Mode")
                date_in = gr.DateTime(label="Date", elem_id="date-in", include_time=False)
                search_btn = gr.Button("Search Doctors", variant="primary")

            with gr.Column(scale=2):
                results = gr.HTML('<div class="placeholder">Select a specialty, date and click Search</div>')

        async def search(specialty, mode, date_val):
            if not specialty:
                return '<div class="placeholder">Please select a specialty</div>'
            if not date_val:
                return '<div class="placeholder">Please pick a date</div>'

            # gr.DateTime returns epoch timestamp — convert to YYYY-MM-DD
            from datetime import datetime
            try:
                if isinstance(date_val, (int, float)):
                    date_str = datetime.fromtimestamp(date_val).strftime("%Y-%m-%d")
                elif isinstance(date_val, str):
                    date_str = date_val[:10]  # already a string, take YYYY-MM-DD part
                else:
                    date_str = str(date_val)[:10]
            except Exception:
                return '<div class="placeholder">Invalid date selected</div>'

            mode_lower = mode.lower()
            try:
                all_docs = await api_get("/doctors/")
                specs = await api_get("/specialties/")
                all_scheds = await api_get("/schedules/")

                spec_map = {s["id"]: s["name"] for s in specs}
                docs = [d for d in all_docs
                        if d.get("active", True)
                        and spec_map.get(d["specialty"], "").lower() == specialty.lower()
                        and d.get("mode", "").lower() == mode_lower]

                if not docs:
                    return f'<div class="placeholder">No {mode} doctors found for {specialty}</div>'

                html = f'<div class="doc-results"><h3>{specialty} — {mode}</h3><p>Date: {date_str}</p>'
                for doc in docs:
                    slots = [s for s in all_scheds
                             if s["doctor"] == doc["id"]
                             and s["date"] == date_str
                             and not s["is_booked"]]

                    if not slots:
                        slots_html = '<span class="no-slots">No available slots on this date</span>'
                    else:
                        slots_html = "".join(
                            f'<button class="slot" onclick="this.classList.toggle(\'selected\')" data-schedule-id="{s["id"]}">{s["time_slot"]}</button>'
                            for s in slots
                        )

                    initial = doc["name"][0] if doc["name"] else "D"
                    html += f'''
                    <div class="doc-card" id="doc-card-{doc["id"]}">
                        <div class="doc-header">
                            <div class="doc-avatar">{initial}</div>
                            <div class="doc-info">
                                <strong>{doc["name"]}</strong>
                                <span>{specialty}</span>
                                <span class="doc-fee">Fee \u20b9{doc["fee"]}</span>
                            </div>
                        </div>
                        <div class="doc-mode-tag {mode_lower}">{mode}</div>
                        <p class="slots-label">Available Slots:</p>
                        <div class="slots">{slots_html}</div>
                        <button class="book-btn" onclick="openBookingForm({doc['id']}, '{doc['name']}', '{doc['fee']}', '{mode_lower}')">Book Appointment</button>
                    </div>'''

                html += '</div>'

                # Add booking modal + JS
                html += '''
                <div id="booking-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:9999; justify-content:center; align-items:center;">
                  <div style="background:#fff; border-radius:16px; padding:28px 32px; max-width:420px; width:90%; box-shadow:0 20px 60px rgba(0,0,0,0.2);">
                    <h3 style="margin:0 0 16px; color:#111827; font-size:1.2rem;">Patient Details</h3>
                    <input id="bk-name" placeholder="Full Name" style="width:100%;padding:10px 14px;margin-bottom:10px;border:1px solid #d1d5db;border-radius:8px;font-size:0.95rem;box-sizing:border-box;">
                    <input id="bk-contact" placeholder="Phone Number" style="width:100%;padding:10px 14px;margin-bottom:10px;border:1px solid #d1d5db;border-radius:8px;font-size:0.95rem;box-sizing:border-box;">
                    <input id="bk-email" placeholder="Email" type="email" style="width:100%;padding:10px 14px;margin-bottom:10px;border:1px solid #d1d5db;border-radius:8px;font-size:0.95rem;box-sizing:border-box;">
                    <label style="font-size:0.85rem;color:#6b7280;display:block;margin-bottom:4px;">Date of Birth</label>
                    <input id="bk-dob" type="date" style="width:100%;padding:10px 14px;margin-bottom:16px;border:1px solid #d1d5db;border-radius:8px;font-size:0.95rem;box-sizing:border-box;">
                    <input id="bk-doctor-id" type="hidden">
                    <input id="bk-fee" type="hidden">
                    <input id="bk-mode" type="hidden">
                    <p id="bk-doc-label" style="font-size:0.85rem;color:#4b5563;margin:0 0 12px;"></p>
                    <p id="bk-slot-label" style="font-size:0.85rem;color:#0d9488;font-weight:600;margin:0 0 16px;"></p>
                    <div style="display:flex;gap:10px;">
                      <button onclick="submitBooking()" style="flex:1;padding:11px;border:none;border-radius:10px;background:#0d9488;color:#fff;font-size:0.95rem;font-weight:600;cursor:pointer;">Confirm Booking</button>
                      <button onclick="closeBookingForm()" style="flex:1;padding:11px;border:1px solid #d1d5db;border-radius:10px;background:#fff;color:#374151;font-size:0.95rem;cursor:pointer;">Cancel</button>
                    </div>
                    <p id="bk-status" style="margin:12px 0 0;font-size:0.9rem;text-align:center;"></p>
                  </div>
                </div>
                <script>
                  let _selectedScheduleId = null;

                  // Slot selection — only allow one selected slot per card
                  document.querySelectorAll(".slot").forEach(btn => {
                    btn.addEventListener("click", function() {
                      // Deselect siblings in same card
                      this.closest(".slots").querySelectorAll(".slot").forEach(s => s.classList.remove("selected"));
                      this.classList.add("selected");
                    });
                  });

                  function openBookingForm(doctorId, doctorName, fee, mode) {
                    // Find the selected slot in this doctor\'s card
                    const card = document.getElementById("doc-card-" + doctorId);
                    const selectedSlot = card ? card.querySelector(".slot.selected") : null;
                    if (!selectedSlot) {
                      alert("Please select a time slot first");
                      return;
                    }
                    _selectedScheduleId = selectedSlot.getAttribute("data-schedule-id");
                    document.getElementById("bk-doctor-id").value = doctorId;
                    document.getElementById("bk-fee").value = fee;
                    document.getElementById("bk-mode").value = mode;
                    document.getElementById("bk-doc-label").textContent = "Doctor: " + doctorName + " | Fee: \u20b9" + fee;
                    document.getElementById("bk-slot-label").textContent = "Slot: " + selectedSlot.textContent;
                    document.getElementById("bk-status").textContent = "";
                    document.getElementById("booking-modal").style.display = "flex";
                  }

                  function closeBookingForm() {
                    document.getElementById("booking-modal").style.display = "none";
                  }

                  async function submitBooking() {
                    const statusEl = document.getElementById("bk-status");
                    const name = document.getElementById("bk-name").value.trim();
                    const contact = document.getElementById("bk-contact").value.trim();
                    const email = document.getElementById("bk-email").value.trim();
                    const dob = document.getElementById("bk-dob").value;
                    if (!name || !contact || !email || !dob) {
                      statusEl.textContent = "Please fill in all fields";
                      statusEl.style.color = "#dc2626";
                      return;
                    }
                    statusEl.textContent = "Booking...";
                    statusEl.style.color = "#6b7280";
                    try {
                      const res = await fetch("/api/book", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({
                          patient_name: name,
                          patient_contact: contact,
                          patient_email: email,
                          patient_dob: dob,
                          doctor_id: parseInt(document.getElementById("bk-doctor-id").value),
                          schedule_id: parseInt(_selectedScheduleId),
                          mode: document.getElementById("bk-mode").value,
                          fee: document.getElementById("bk-fee").value
                        })
                      });
                      const data = await res.json();
                      if (data.success) {
                        statusEl.style.color = "#059669";
                        statusEl.textContent = data.message;
                        setTimeout(() => closeBookingForm(), 2500);
                      } else {
                        statusEl.style.color = "#dc2626";
                        statusEl.textContent = "Error: " + (data.error || "Booking failed");
                      }
                    } catch(err) {
                      statusEl.style.color = "#dc2626";
                      statusEl.textContent = "Network error: " + err.message;
                    }
                  }
                </script>
                '''
                return html

            except Exception as e:
                import traceback
                traceback.print_exc()
                return f'<div class="placeholder">Error fetching data: {e}</div>'

        search_btn.click(search, [specialty_dd, mode_dd, date_in], results)

        # Pre-fill specialty from URL
        def prefill_specialty(request: gr.Request):
            params = dict(request.query_params) if request else {}
            spec = params.get("specialty", "").replace("+", " ")
            names = get_specialty_names()
            return gr.Dropdown(value=spec) if spec in names else gr.Dropdown()

        demo.load(prefill_specialty, None, specialty_dd)

    return demo


# ---------------------------------------------------------------------------
# Mount
# ---------------------------------------------------------------------------
booking_ui = _booking()
home_ui = _home()
app = gr.mount_gradio_app(app, booking_ui, path="/booking")
app = gr.mount_gradio_app(app, home_ui, path="/")
