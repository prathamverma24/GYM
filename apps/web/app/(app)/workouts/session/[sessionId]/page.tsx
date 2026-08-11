"use client";

import { useParams } from "next/navigation";
import { LiveWorkout } from "@/features/workouts/live-workout";

export default function WorkoutSessionPage() { const { sessionId } = useParams<{ sessionId: string }>(); return <LiveWorkout sessionId={sessionId} />; }

