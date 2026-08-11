import "@fontsource/poppins/400.css";
import "@fontsource/poppins/500.css";
import "@fontsource/poppins/600.css";
import "@fontsource/poppins/700.css";
import "./globals.css";

import type { Metadata, Viewport } from "next";

import { Providers } from "@/components/providers";
import { ServiceWorkerRegistration } from "@/components/service-worker";

export const metadata: Metadata = {
  title: { default: "AthleteOS — Train with clarity", template: "%s · AthleteOS" },
  description: "A personalized operating system for training, nutrition, habits and progress.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#0b1020",
  colorScheme: "dark",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <Providers>{children}</Providers>
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
