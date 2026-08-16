import streamlit as st
import os
import time
import logging
import pandas as pd
from services.auth.login_wall import render_login_wall
from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.ui.style_loader import load_css,inject_local_font,inject_webrtc_styles
from services.persistence.exercise_repository import init_db
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update
from services.persistence.exercise_repository import get_users_exercises
from groq import Groq
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import VoicePipeline, autoplay_audio, store_coaching_result

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")



def main():
    st.set_page_config(
        page_icon="🏋️",
        page_title="AI Real-time GYM Trainer",
        initial_sidebar_state="expanded",
        layout="centered"
    )


    load_css(os.path.join(os.getcwd(),"static","style.css"))
    inject_local_font(
    os.path.join(os.getcwd(), "static", "AdobeClean.otf"),
    "AdobeClean"
)

    init_db()
    
    if not render_login_wall():
        return

    initial_session_defaults()

    if "voice_pipeline" not in st.session_state:
        try:
            api_key = os.environ.get("GROQ_API_KEY", "")

            if not api_key:
                try:
                    if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                        api_key = st.secrets["GROQ_API_KEY"]
                except Exception:
                    pass

            if not api_key:
                st.error("GROQ_API_KEY not found. Set it in environment variables or Streamlit secrets.")
                st.session_state.voice_pipeline = None
            else:
                groq_client = Groq(api_key=api_key)
                llm_coach = LLMCoach(groq_client)
                tts = TextToSpeech()
                st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)

        except Exception as e:
            st.error(f"Failed to initialize AI Coach: {e}")
            st.session_state.voice_pipeline = None

    # ------------------------------------------------------------------
    # AI COACH AUDIO PLAYBACK
    # Rendered at the TOP of the script so it runs on EVERY rerun,
    # including the frequent video-loop reruns (which call st.rerun()).
    # audio_to_play is intentionally NOT cleared: st.audio is re-rendered
    # at the same position each run, so Streamlit keeps the same <audio>
    # element alive (playback continues across reruns). A NEW coaching
    # message replaces audio_to_play with new bytes -> the element's src
    # changes -> the new message autoplays exactly once.
    # ------------------------------------------------------------------
    audio_to_play = st.session_state.get("audio_to_play")
    if audio_to_play:
        autoplay_audio(audio_to_play)

    if st.session_state.get("coach_feedback"):
        st.markdown("")
        st.success(f"🤖 **Coach:** {st.session_state.coach_feedback}")

    with st.expander("AI Coach Diagnostics (Debug)", expanded=False):
        audio_debug = st.session_state.get("audio_debug", {})
        st.caption(
            f"TTS status: {audio_debug.get('status', 'N/A')} | "
            f"Audio: {'YES' if audio_debug.get('size') else 'NO'} "
            f"({audio_debug.get('size', 0)} bytes) | "
            f"Format: {audio_debug.get('format', 'N/A')} | "
            f"Event id: {st.session_state.get('audio_event_id', 0)}"
        )
        if audio_debug.get("text"):
            st.caption(f"Last coaching text: {audio_debug['text']}")

        if st.button("Test AI Coach Voice", key="test_coach_voice"):
            pipeline = st.session_state.get("voice_pipeline")
            if pipeline is None:
                st.error("AI Coach is not initialized. Set GROQ_API_KEY and restart.")
            else:
                pipeline.last_spoken_at = 0
                pipeline.last_issue = None
                pipeline.last_event = None
                result = pipeline.process_event(
                    event="ongoing_form_check",
                    exercise=st.session_state.get("exercise_type", "Squats"),
                    metrics={"issue": "manual voice test"},
                )
                if result:
                    audio, _feedback = result
                    store_coaching_result(result)
                    st.success(f"Voice test OK — {len(audio)} bytes of audio generated.")
                    autoplay_audio(audio)
                else:
                    st.error("Voice test FAILED — no audio generated. Check the terminal logs.")

    workout_started = st.session_state.get("workout_started", False)

    with st.sidebar:
        st.title("🏋️ Your AI Coach")

        if st.session_state.username:
            st.caption(f" 👤 Login as {st.session_state.username}")

        st.divider()

        st.subheader("Workout Plan")
        if not workout_started:
            plan_exercise = st.selectbox("Exercise",options=EXERCISE_OPTIONS,key="plan_exercise",placeholder="Enter exercise name")

            plan_sets = st.number_input("Sets", min_value=0,max_value=50,key="plan_sets",step=1)

            plan_reps = st.number_input("Reps", min_value=0,max_value=50,key="plan_reps",step=1)

            st.markdown("")

            start_session_button = st.button("Start Workout",width="stretch",key="start_session_button")

            if start_session_button:
                st.session_state.exercise_type = plan_exercise
                st.session_state.workout_started = True
                st.session_state.reps = 0
                st.session_state.target_sets = int(plan_sets)
                st.session_state.reps_per_set = int(plan_reps)
                st.session_state.set_cycle_started_at = time.time()
                st.session_state.last_saved_sets_completed = 0

                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_started",
                        exercise=plan_exercise,
                        metrics={},
                    )

                    store_coaching_result(result)

                st.session_state.last_notified_sets_completed = 0
                st.session_state.last_notified_workout_complete = False
                st.rerun()
        
        else:
            exercise = st.session_state.get("exercise_type")
            sets = st.session_state.get("target_sets")
            reps = st.session_state.get("reps_per_set")

            st.info(f"**{exercise}** - {sets} Sets / {reps} Reps")

            end_session_button = st.button("End Workout",key="end_session_button",width="stretch")

            if end_session_button:
                st.session_state.workout_started = False

                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_completed",
                        exercise=exercise,
                        metrics={},
                    )

                    store_coaching_result(result)
                st.rerun()

        if workout_started:
            st.divider()

            exercise = st.session_state.get("exercise_type")
            total_reps = st.session_state.get("reps")
            current_set_reps = st.session_state.get("current_set_reps")
            reps_per_set = st.session_state.get("reps_per_set")
            sets_completed = st.session_state.get("sets_completed")
            target_sets = st.session_state.get("target_sets")

            st.subheader("Progress")

            st.metric("Total Reps", f"{total_reps}")
            st.metric("Current Set Reps", f"{current_set_reps}/{reps_per_set}")
            st.metric("Sets Completed", f"{sets_completed}/{target_sets}")

            st.divider()

            if exercise == "Squats":
                            st.subheader("Squat Metrics")
                            st.metric("Knee Angle", f"{st.session_state.knee_angle}°")
                            st.metric("Back Angle", f"{st.session_state.back_angle}°")
                            st.metric("Depth Status", st.session_state.depth_status)
            
            elif exercise == "Push-ups":
                            st.subheader("Push-up Metrics")
                            st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                            st.metric("Body Alignment", st.session_state.body_alignment)
                            st.metric("Hip Position", st.session_state.hip_status)
            
            elif exercise == "Bicep Curls (Dumbbell)":
                            st.subheader("Curl Metrics")
                            st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                            st.metric("Shoulder Stability", st.session_state.shoulder_status)
                            st.metric("Swing Detection", st.session_state.swing_status)
            
            elif exercise == "Shoulder Press":
                            st.subheader("Shoulder Press Metrics")
                            st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                            st.metric("Arm Extension", st.session_state.extension_status)
                            st.metric("Back Arch", st.session_state.back_arch_status)
            
            elif exercise == "Lunges":
                            st.subheader("Lunge Metrics")
                            st.metric("Front Knee Angle", f"{st.session_state.front_knee_angle}°")
                            st.metric("Torso Angle", f"{st.session_state.torso_angle}°")
                            st.metric("Balance Status", st.session_state.balance_status)
    st.markdown(
    """
    <style>
    h1 {
        text-align: center;
    }

    h4 {
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


    st.title("AI Real-time GYM Coach")
    st.markdown("#### Real-time pose detection with proactive AI voice coaching")

    if not workout_started:
        st.markdown(
        """
        <div style="
            width: 75%;
            margin: 32px auto 0 auto;
            border: 10px dashed #444;
            border-radius: 0px;
            padding: 48px 32px;
            text-align: center;
            color: #888;
            box-sizing: border-box;
        ">
            <h2 style="color:#ccc; margin-bottom:8px;">👉 Set your workout plan</h2>
            <p style="font-size:1.05rem;">
                Choose your exercise, sets and reps in the sidebar,<br>
                then click <strong>Start Workout</strong> to activate the camera and AI coach.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    else:
        exercise = st.session_state.get("exercise_type", "Squats")
        
        def processor_factory():
            processor = VideoProcessorClass()
            processor.set_exercise(exercise)
            return processor
        
        context = webrtc_streamer(
                key = "exercise-analysis",
                mode = WebRtcMode.SENDRECV,
                video_processor_factory=processor_factory,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                media_stream_constraints={
                        "video":True,
                        "audio":False
                },
                async_processing=True
        )


        sync_metrics_update(context)

        if context.state.playing:
                time.sleep(0.25)
                st.rerun()

        inject_webrtc_styles()

    st.divider()

    user_id = st.session_state.get("user_id", 0)

    if isinstance(user_id,int):
           history_rows = get_users_exercises(user_id)

           arr = [

                  {
                         "Exercise" : row['exercise_name'],
                         "Reps": row['reps'],
                         "Sets": row['sets'],
                         "Time (sec)": row['time'],
                         "Date": row['created_at']
                  }
                  for row in history_rows
            ]

           df = pd.DataFrame(arr)

           if not df.empty:
                  df["Date"]= pd.to_datetime(df["Date"]).dt.date
                  agg_df = df.groupby(["Exercise","Date"]).agg({"Reps":"sum","Sets":"sum","Time (sec)":"sum"}).reset_index()
                  agg_df.index +=1

                  st.table(df,border="horizontal")
           else:
                  st.info("No workout history found. Start your first workout to see the history here.")
    st.markdown("#### Workout History")


if __name__ == "__main__":
    main()