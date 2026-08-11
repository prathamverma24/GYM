# Computer Vision Pipeline

The body-scan feature runs only after explicit user action. It lazy-loads MediaPipe Pose Landmarker, checks image resolution/framing and required landmark visibility, then derives normalized 2D ratios and alignment signals. Only the versioned derived payload is submitted.

Raw media storage is disabled in the MVP. No face recognition, medical diagnosis, body-type label, clinically validated body-fat claim, or exact circumference inference is made. Camera position, clothing, lighting and lens distortion can materially affect results; incompatible or low-confidence scans are not compared.

