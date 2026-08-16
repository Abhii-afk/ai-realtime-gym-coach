from core.base_exercise import BaseExercise


class ShoulderPressDetector(BaseExercise):
    DOWN_THRESHOLD = 110
    UP_THRESHOLD = 160
    MIN_VISIBILITY = 0.7

    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26

    def __init__(self):
        super().__init__()

    def reset(self):
        self.reps = 0
        self.stage = None

    def process(self, landmarks):
        left_elbow_angle = self.calculate_angle(
            self.get_point(landmarks, self.LEFT_SHOULDER),
            self.get_point(landmarks, self.LEFT_ELBOW),
            self.get_point(landmarks, self.LEFT_WRIST),
        )
        right_elbow_angle = self.calculate_angle(
            self.get_point(landmarks, self.RIGHT_SHOULDER),
            self.get_point(landmarks, self.RIGHT_ELBOW),
            self.get_point(landmarks, self.RIGHT_WRIST),
        )

        left_vis = landmarks[self.LEFT_ELBOW].visibility
        right_vis = landmarks[self.RIGHT_ELBOW].visibility

        if left_vis >= right_vis:
            elbow_angle = left_elbow_angle
            shoulder_idx, elbow_idx, wrist_idx, hip_idx, knee_idx = (
                self.LEFT_SHOULDER,
                self.LEFT_ELBOW,
                self.LEFT_WRIST,
                self.LEFT_HIP,
                self.LEFT_KNEE,
            )
        else:
            elbow_angle = right_elbow_angle
            shoulder_idx, elbow_idx, wrist_idx, hip_idx, knee_idx = (
                self.RIGHT_SHOULDER,
                self.RIGHT_ELBOW,
                self.RIGHT_WRIST,
                self.RIGHT_HIP,
                self.RIGHT_KNEE,
            )

        torso_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, knee_idx),
        )

        key_landmark_visible = (
            landmarks[shoulder_idx].visibility >= self.MIN_VISIBILITY
            and landmarks[elbow_idx].visibility >= self.MIN_VISIBILITY
            and landmarks[wrist_idx].visibility >= self.MIN_VISIBILITY
        )

        if key_landmark_visible:
            if elbow_angle < self.DOWN_THRESHOLD:
                self.stage = "down"

            if elbow_angle >= self.UP_THRESHOLD and self.stage == "down":
                self.stage = "up"
                self.reps += 1

        extension_status = "FULL EXTENSION" if elbow_angle >= self.UP_THRESHOLD else "BENT ARM"
        back_arch_status = "GOOD POSTURE" if torso_angle <= 150 else "BACK ARCHED"

        return {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle),
            "extension_status": extension_status,
            "back_arch_status": back_arch_status,
        }
