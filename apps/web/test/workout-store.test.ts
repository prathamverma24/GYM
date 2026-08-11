import { beforeEach, describe, expect, it } from "vitest";

import { useWorkoutStore } from "@/features/workouts/workout-store";

describe("workout draft outbox", () => {
  beforeEach(() => {
    localStorage.clear();
    useWorkoutStore.setState({ drafts: {} });
  });

  it("keeps client operation IDs while a set moves from draft to saved", () => {
    const operationId = "operation-123";
    useWorkoutStore.getState().replace("session", [{
      prescribed_exercise_id: "prescription",
      set_index: 1,
      client_operation_id: operationId,
      load_kg: 60,
      reps: 8,
      seconds: null,
      rir: 2,
      completed: false,
      sync: "draft",
    }]);
    useWorkoutStore.getState().update("session", operationId, { completed: true, sync: "saved", id: "server-id" });
    const row = useWorkoutStore.getState().drafts.session[0];
    expect(row.client_operation_id).toBe(operationId);
    expect(row.sync).toBe("saved");
    expect(row.id).toBe("server-id");
  });
});

