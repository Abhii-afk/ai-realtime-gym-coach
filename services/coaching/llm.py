from services.config.workout_config import PROMPT
import logging

logger = logging.getLogger(__name__)


class LLMCoach:
    def __init__(self, groq_client):
        self.client = groq_client
        self.history = []
        self.system_prompt = PROMPT

    def give_feedback(self, event, exercise, issue):
        if event == "workout_completed":
            text = "Incredible job! You smashed the workout!"
            self.history.append({"role": "assistant", "content": text})
            return text

        if event == "workout_started":
            prompt = f"Event: {event}"
        elif event == "set_completed":
            prompt = f"Event: {event}"
        elif event == "workout_completed":
            prompt = f"Event: {event}"
        elif event == "no_pose_detected":
            prompt = f"Event: {event} Form Issue: {issue}"
        elif event == "ongoing_form_check":
            if issue:
                prompt = f"Event: {event} Form Issue: {issue}"
            else:
                prompt = f"Event: {event}"
        else:
            prompt = f"Event: {event}"

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history[-10:],
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.4,
            )
            text = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return self._fallback_response(event, issue)

        self.history.append({"role": "assistant", "content": text})

        return text

    def _fallback_response(self, event, issue):
        fallbacks = {
            "workout_started": "Let's get started! Strong and steady.",
            "set_completed": "Great set! Keep that momentum going.",
            "workout_completed": "Incredible job! You smashed the workout!",
            "no_pose_detected": "Step into the frame so I can see you.",
            "ongoing_form_check": f"Fix: {issue}" if issue else "Looking good, keep it up!",
        }
        return fallbacks.get(event, "Stay focused!")