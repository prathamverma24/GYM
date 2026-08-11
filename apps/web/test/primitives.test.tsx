import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState, MetricCard } from "@/components/primitives";

describe("dashboard primitives", () => {
  it("renders metric values with explicit units", () => {
    render(<MetricCard label="Weight" value="72.5" unit="kg" note="Latest measurement" />);
    expect(screen.getByText("Weight")).toBeInTheDocument();
    expect(screen.getByText("72.5")).toHaveTextContent("72.5kg");
    expect(screen.getByText("Latest measurement")).toBeInTheDocument();
  });

  it("renders actionable empty-state guidance", () => {
    render(<EmptyState title="No workouts yet" message="Generate a program to begin." action={<button>Generate</button>} />);
    expect(screen.getByRole("heading", { name: "No workouts yet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate" })).toBeEnabled();
  });
});

