import type { Metadata } from "next";

import { OnboardingWizard } from "@/features/onboarding/onboarding-wizard";

export const metadata: Metadata = { title: "Build your athlete profile" };

export default function OnboardingPage() { return <OnboardingWizard />; }

