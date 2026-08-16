import time
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class VoicePipeline:
    def __init__(self, llm, tts):
        self.llm = llm
        self.tts = tts
        self.last_spoken_at = 0
        self.last_issue = None
        self.last_event = None
        self.min_interval_seconds = 8

    def _find_form_issue(self, exercise, metrics):
        if "issue" in metrics:
            return metrics["issue"]

        if exercise == "Squats":
            depth = metrics.get("depth_status", "")
            back_angle = metrics.get("back_angle", 180)

            if depth == "TOO HIGH":
                return "The user's squat is not deep enough — knees are not bending sufficiently."

            if isinstance(back_angle, (int, float)) and back_angle < 130:
                return "The user is leaning too far forward during the squat."

        elif exercise == "Push-ups":
            alignment = metrics.get("body_alignment", "")
            hip_status = metrics.get("hip_status", "")

            if alignment == "MISALIGNED":
                return "The user's body is not straight during the push-up."

            if hip_status == "LOW / HIGH":
                return "The user's hips are not level during the push-up."

        elif exercise == "Bicep Curls (Dumbbell)":
            swing = metrics.get("swing_status", "")
            shoulder = metrics.get("shoulder_status", "")

            if swing == "SWINGING":
                return "The user is swinging their torso during the curl — keep the body still."

            if shoulder == "DRIFTING":
                return "The user's elbow is drifting away from their side during the curl."

        elif exercise == "Shoulder Press":
            back_arch = metrics.get("back_arch_status", "")
            extension = metrics.get("extension_status", "")

            if back_arch == "BACK ARCHED":
                return "The user is arching their lower back excessively during the press."

        elif exercise == "Lunges":
            balance = metrics.get("balance_status", "")

            if balance == "UNBALANCED":
                return "The user is losing balance during the lunge — feet should be hip-width apart."

        return None

    def _should_speak(self, event, issue):
        now = time.time()

        is_major_event = event in ["workout_started", "set_completed", "workout_completed", "no_pose_detected"]

        if is_major_event:
            if now - self.last_spoken_at >= self.min_interval_seconds:
                logger.info(f"VoicePipeline: Major event '{event}' - enough time passed, will speak")
                return True
            logger.debug(f"VoicePipeline: Major event '{event}' throttled (last: {now - self.last_spoken_at:.1f}s ago)")
            return False

        if not issue:
            logger.debug(f"VoicePipeline: No form issue for '{event}', skipping")
            return False

        if issue == self.last_issue and event == self.last_event:
            if now - self.last_spoken_at < self.min_interval_seconds:
                logger.debug(f"VoicePipeline: Same issue '{issue}' throttled (last: {now - self.last_spoken_at:.1f}s ago)")
                return False

        logger.info(f"VoicePipeline: Will speak for event='{event}', issue='{issue}'")
        return True

    def process_event(self, event, exercise, metrics):
        logger.info(f"VoicePipeline.process_event: event='{event}', exercise='{exercise}'")
        issue = self._find_form_issue(exercise, metrics)
        logger.debug(f"VoicePipeline: Found issue: {repr(issue)}")

        if not self._should_speak(event, issue):
            return None

        try:
            text = self.llm.give_feedback(event, exercise, issue)
        except Exception as e:
            logger.error(f"LLMCoach error: {e}", exc_info=True)
            return None

        if not text:
            logger.warning("LLMCoach returned empty text")
            return None

        logger.info(f"VoicePipeline: LLM generated feedback: {repr(text)}")

        try:
            voice = self.tts.speak(text)
        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
            return None

        if not voice:
            logger.warning("TTS returned empty audio")
            return None

        logger.info(f"VoicePipeline: Generated audio: {len(voice)} bytes")

        self.last_spoken_at = time.time()
        self.last_issue = issue
        self.last_event = event

        return voice, text


def autoplay_audio(audio_bytes):
    """Play audio using Streamlit's native st.audio().

    IMPORTANT: audio_to_play must be kept in session_state (not cleared)
    so that st.audio is re-rendered at the same position on every rerun.
    Streamlit's frontend keeps the same <audio> element alive and only
    restarts playback when the audio bytes change (i.e. a new coaching
    message), which prevents the frequent video-loop reruns from cutting
    off playback while also preventing repeat playback of the same message.
    """
    if not audio_bytes:
        logger.warning("autoplay_audio: No audio bytes provided")
        return

    logger.info(f"autoplay_audio: Rendering {len(audio_bytes)} bytes via st.audio")
    st.audio(audio_bytes, format="audio/mpeg", autoplay=True)


def store_coaching_result(result):
    """Store (audio, text) from process_event into session_state.

    Guarantees a consistent (audio, feedback) contract and tracks an
    incrementing event id so each coaching message is played exactly once.
    """
    if not result:
        return

    audio, feedback = result
    st.session_state.audio_to_play = audio
    st.session_state.coach_feedback = feedback
    st.session_state.audio_event_id = st.session_state.get("audio_event_id", 0) + 1
    st.session_state.audio_debug = {
        "status": "SUCCESS",
        "size": len(audio) if audio else 0,
        "format": "MP3",
        "text": feedback,
    }
    logger.info(
        f"store_coaching_result: audio={len(audio) if audio else 0}B "
        f"feedback={repr(feedback)} event_id={st.session_state.audio_event_id}"
    )