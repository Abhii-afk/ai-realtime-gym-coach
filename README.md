# AI Real-time GYM Coach

AI Real-time GYM Coach is a Streamlit application that performs real-time pose detection and provides proactive voice coaching for common strength exercises. It uses an on-device pose landmarker model to compute exercise metrics (reps, angles, form issues) and a small pipeline (LLM -> TTS) to produce short spoken coaching cues during the workout.

Key features
- Live webcam video with pose detection and skeleton overlay
- Real-time detector modules for Squats, Push-ups, Bicep Curls, Shoulder Press, Lunges
- Automatic rep counting and simple form checks
- Voice coaching pipeline: LLM (Groq client) -> text feedback -> TTS (gTTS) -> streamed audio
- Per-user workout persistence in a local SQLite DB
- Debug UI panel to test the AI coach

Quick links
- Entrypoint: [main.py](d:/AI-Realtime-Gym-Coach/main.py)
- Vision processor & video loop: [services/vision/exercise_video_processor.py](d:/AI-Realtime-Gym-Coach/services/vision/exercise_video_processor.py)
- Voice pipeline & TTS: [services/coaching/voice_pipeline.py](d:/AI-Realtime-Gym-Coach/services/coaching/voice_pipeline.py) and [services/coaching/tts.py](d:/AI-Realtime-Gym-Coach/services/coaching/tts.py)
- LLM wrapper for Groq: [services/coaching/llm.py](d:/AI-Realtime-Gym-Coach/services/coaching/llm.py)
- Exercise detectors: [detectors/](d:/AI-Realtime-Gym-Coach/detectors)
- SQLite persistence: [services/persistence/exercise_repository.py](d:/AI-Realtime-Gym-Coach/services/persistence/exercise_repository.py)
- Example UI helpers & styling: [services/ui/style_loader.py](d:/AI-Realtime-Gym-Coach/services/ui/style_loader.py)
- Default config/prompt: [services/config/workout_config.py](d:/AI-Realtime-Gym-Coach/services/config/workout_config.py)
- ML model (required): `ml_models/pose_landmarker_full.task` (commit excluded due to size)

Prerequisites
- Python 3.10+ (recommend 3.10–3.11 for better binary compatibility with MediaPipe)
- Git
- FFmpeg must be installed and available in PATH for pyav/stream handling on some platforms
- Recommended: use a virtual environment

Core Python dependencies (inferred from imports)
- streamlit
- streamlit-webrtc
- mediapipe
- opencv-python
- av (pyav)
- numpy
- pandas
- gTTS
- groq (Groq Python client)

(There may be additional transitive dependencies. Adding a requirements.txt or pyproject.toml is recommended.)

Suggested setup (Windows PowerShell)
1. Create and activate a virtual environment:
   - python -m venv .venv
   - .venv\Scripts\Activate.ps1

2. Install packages (example):
   - pip install streamlit streamlit-webrtc mediapipe opencv-python av numpy pandas gTTS groq

   Note: On Windows some packages (pyav, mediapipe) are easier to install from wheels or via conda. If pip install fails, check the package docs.

3. Ensure FFmpeg is installed and on PATH:
   - Download FFmpeg from https://ffmpeg.org and add to PATH (or install via package manager).

4. Place the MediaPipe pose model
   - Ensure the file exists: d:/AI-Realtime-Gym-Coach/ml_models/pose_landmarker_full.task
   - This repository expects that file to be present. If you have a different model path, update the path in [services/vision/exercise_video_processor.py](d:/AI-Realtime-Gym-Coach/services/vision/exercise_video_processor.py) where `model_path` is constructed.

5. Set the GROQ API key (used by the LLM wrapper)
   - Recommended (local): create `.streamlit/secrets.toml` in the project root:
     ```toml
     GROQ_API_KEY = "YOUR_GROQ_KEY"
     ```
   - Or set an environment variable:
     - PowerShell (temporary): `$env:GROQ_API_KEY = "YOUR_GROQ_KEY"`
     - Permanent (Windows): `setx GROQ_API_KEY "YOUR_GROQ_KEY"` (restart shells)
   - For Streamlit Cloud: add the secret using the app's Secrets settings in the Streamlit Cloud dashboard with the same key name `GROQ_API_KEY`.

6. Run the app:
   - `streamlit run main.py`

Behavior notes
- On startup `main.py` looks for `GROQ_API_KEY` first in the environment and then in `st.secrets` (Streamlit secrets). If not found, the AI Coach will not initialize and an error banner appears on the UI.
- The app automatically creates/uses a local SQLite DB at `d:/AI-Realtime-Gym-Coach/data.db`. User accounts are simple unique username strings.
- The TTS uses gTTS (Google TTS). The produced audio is cached in-memory per session to avoid repeated calls.

Project structure (high level)
- `main.py` — Streamlit entrypoint, session initialization, UI layout
- `services/` — application logic for UI, vision processing, coaching, persistence, config
- `detectors/` — per-exercise logic that derives metrics from pose landmarks
- `ml_models/` — pose landmarker model file (not committed)
- `data.db` — SQLite DB used for persistence (created automatically)
- `static/` — fonts and CSS
- `.streamlit/secrets.toml` — (should be gitignored) stores `GROQ_API_KEY` locally

Security & repository hygiene
- Do NOT commit API keys or secrets. Add these to `.gitignore`:
  - `.env`
  - `.streamlit/secrets.toml`
  - `.venv/`
- If a secret was accidentally committed, rotate the secret immediately and consider rewriting git history.

Common troubleshooting
- App shows "GROQ_API_KEY not found. Set it in environment variables or Streamlit secrets."  
  - Fix: add the key to `.streamlit/secrets.toml` or set the environment variable `GROQ_API_KEY`, then restart the Streamlit server.
- MediaPipe or av install fails on Windows  
  - Try installing from prebuilt wheels or use a conda environment. Ensure Visual C++ build tools are installed.  
  - Make sure FFmpeg is installed and on PATH; `pyav` requires ffmpeg/libav.
- Camera stream or audio not working  
  - Check browser permissions, use a supported browser, and ensure `streamlit-webrtc` can access the device. Some corporate/VM environments restrict direct camera access.
- Very slow performance / model loading issues  
  - The app uses a local MediaPipe task model. Ensure the model file is present and CPU/GPU constraints are known. Performance will vary by CPU and OS.

Development notes & suggestions
- Add a `requirements.txt` (e.g., `pip freeze > requirements.txt`) or `pyproject.toml` to lock dependencies.
- Consider replacing gTTS with an offline TTS for faster, private audio in production (e.g., local TTS or commercial TTS with a managed key).
- Break the LLM/Voice pipeline into a background worker if you expect heavy usage.
- Add tests for detector modules (unit test landmarks -> metric outputs).
- If deploying to Streamlit Cloud, set `GROQ_API_KEY` in the app settings rather than uploading `secrets.toml` to a public repo.

How to contribute
1. Fork the repository
2. Create a feature branch
3. Open a pull request with a clear description and changes
4. Add or update tests for any new logic

License
- Add your preferred license here (MIT, Apache-2.0, etc.). Currently unspecified.

Contact
- For questions about the code, open an issue or contact the maintainer (add contact details here).
