"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { SetLog } from "@/types/api";

export type DraftSet = SetLog & { sync: "draft" | "pending" | "saved" | "error" };

type WorkoutState = {
  drafts: Record<string, DraftSet[]>;
  replace: (sessionId: string, sets: DraftSet[]) => void;
  update: (sessionId: string, operationId: string, values: Partial<DraftSet>) => void;
  remove: (sessionId: string, operationId: string) => void;
  clear: (sessionId: string) => void;
};

export const useWorkoutStore = create<WorkoutState>()(
  persist(
    (set) => ({
      drafts: {},
      replace: (sessionId, sets) => set((state) => ({ drafts: { ...state.drafts, [sessionId]: sets } })),
      update: (sessionId, operationId, values) => set((state) => ({ drafts: { ...state.drafts, [sessionId]: (state.drafts[sessionId] ?? []).map((item) => item.client_operation_id === operationId ? { ...item, ...values } : item) } })),
      remove: (sessionId, operationId) => set((state) => ({ drafts: { ...state.drafts, [sessionId]: (state.drafts[sessionId] ?? []).filter((item) => item.client_operation_id !== operationId) } })),
      clear: (sessionId) => set((state) => { const drafts = { ...state.drafts }; delete drafts[sessionId]; return { drafts }; }),
    }),
    { name: "athleteos-active-workouts" },
  ),
);

