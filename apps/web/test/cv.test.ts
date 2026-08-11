import { describe, expect, it } from "vitest";

import { planPoseInput } from "@/lib/cv";

describe("pose input preparation", () => {
  it("accepts and safely upscales a clear phone-sized image", () => {
    expect(planPoseInput(360, 540)).toEqual({
      width: 480,
      height: 720,
      scale: 4 / 3,
      upscaled: true,
    });
  });

  it("leaves sufficiently large images unchanged", () => {
    expect(planPoseInput(1080, 1920)).toEqual({
      width: 1080,
      height: 1920,
      scale: 1,
      upscaled: false,
    });
  });

  it("rejects only genuinely unusable thumbnails", () => {
    expect(() => planPoseInput(120, 160)).toThrow(/240 pixels on the short edge/);
  });
});
