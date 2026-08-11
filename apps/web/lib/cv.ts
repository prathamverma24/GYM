export type ScanAnalysis = {
  modelVersion: string;
  qualityScore: number;
  confidence: number;
  qualityFlags: string[];
  features: Record<string, number>;
};

type Landmark = { x: number; y: number; z: number; visibility?: number };

export type PoseInputPlan = {
  width: number;
  height: number;
  scale: number;
  upscaled: boolean;
};

export function planPoseInput(width: number, height: number): PoseInputPlan {
  const shortSide = Math.min(width, height);
  const longSide = Math.max(width, height);
  if (!Number.isFinite(width) || !Number.isFinite(height) || shortSide < 240 || longSide < 320) {
    throw new Error(
      `This image is only ${Math.max(0, Math.round(width))} × ${Math.max(0, Math.round(height))} pixels. Choose one at least 240 pixels on the short edge and 320 on the long edge.`,
    );
  }
  const scale = Math.max(1, 480 / shortSide, 640 / longSide);
  return {
    width: Math.round(width * scale),
    height: Math.round(height * scale),
    scale,
    upscaled: scale > 1,
  };
}

function distance(a: Landmark, b: Landmark) { return Math.hypot(a.x - b.x, a.y - b.y); }
function angle(a: Landmark, b: Landmark) { return Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI; }

export async function analyzePose(image: HTMLImageElement): Promise<ScanAnalysis> {
  if (!image.complete || !image.naturalWidth || !image.naturalHeight) {
    await image.decode();
  }
  const inputPlan = planPoseInput(image.naturalWidth, image.naturalHeight);
  let poseInput: TexImageSource = image;
  if (inputPlan.upscaled) {
    const canvas = document.createElement("canvas");
    canvas.width = inputPlan.width;
    canvas.height = inputPlan.height;
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) throw new Error("This browser could not prepare the image for analysis.");
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    poseInput = canvas;
  }
  const { FilesetResolver, PoseLandmarker } = await import("@mediapipe/tasks-vision");
  const vision = await FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm");
  const options = {
    baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task" },
    runningMode: "IMAGE" as const,
    numPoses: 1,
    minPoseDetectionConfidence: 0.45,
    minPosePresenceConfidence: 0.45,
    minTrackingConfidence: 0.45,
    outputSegmentationMasks: false,
  };
  let landmarker;
  try {
    landmarker = await PoseLandmarker.createFromOptions(vision, {
      ...options,
      baseOptions: { ...options.baseOptions, delegate: "GPU" },
    });
  } catch {
    landmarker = await PoseLandmarker.createFromOptions(vision, options);
  }
  let result;
  try {
    result = landmarker.detect(poseInput);
  } finally {
    landmarker.close();
  }
  if (!result.landmarks.length) throw new Error("No complete person was detected. Use an uncluttered background and retake the photo.");
  const points = result.landmarks[0] as Landmark[];
  const required = [points[11], points[12], points[23], points[24]];
  const confidence = required.reduce((total, point) => total + (point.visibility ?? 0.5), 0) / required.length;
  const flags: string[] = inputPlan.upscaled ? ["Source image was safely upscaled for pose detection"] : [];
  if (confidence < 0.65) flags.push("Low torso landmark confidence");
  if (required.some((point) => point.x < 0.035 || point.x > 0.965 || point.y < 0.035 || point.y > 0.965)) flags.push("Body is too close to an image edge");
  const shoulderWidth = distance(points[11], points[12]);
  const hipWidth = distance(points[23], points[24]);
  const shoulderMid = { x: (points[11].x + points[12].x) / 2, y: (points[11].y + points[12].y) / 2, z: 0 };
  const hipMid = { x: (points[23].x + points[24].x) / 2, y: (points[23].y + points[24].y) / 2, z: 0 };
  const torsoLength = distance(shoulderMid, hipMid);
  if (torsoLength < 0.12) flags.push("Camera framing makes the torso too small for comparison");
  const rotationProxy = Math.abs(points[11].z - points[12].z);
  if (rotationProxy > 0.16) flags.push("Torso rotation may affect width ratios");
  const qualityScore = Math.max(0, Math.min(100, Math.round(confidence * 78 + Math.min(torsoLength / 0.3, 1) * 22 - flags.length * 9)));
  const features = {
    shoulder_to_hip_ratio: Number((shoulderWidth / Math.max(hipWidth, 0.001)).toFixed(4)),
    torso_inclination_deg: Number((angle(shoulderMid, hipMid) - 90).toFixed(2)),
    shoulder_line_angle_deg: Number(angle(points[11], points[12]).toFixed(2)),
    hip_line_angle_deg: Number(angle(points[23], points[24]).toFixed(2)),
    landmark_symmetry: Number(Math.max(0, 1 - Math.abs(Math.abs(points[11].x - shoulderMid.x) - Math.abs(points[12].x - shoulderMid.x)) / Math.max(shoulderWidth, 0.001)).toFixed(4)),
    pose_rotation_proxy: Number(rotationProxy.toFixed(4)),
  };
  return { modelVersion: "mediapipe-pose-landmarker-lite-float16-v1", qualityScore, confidence: Number(confidence.toFixed(4)), qualityFlags: flags, features: qualityScore >= 60 && confidence >= 0.55 ? features : {} };
}
