import Link from "next/link";

import { Brand, Card } from "@/components/primitives";

export function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle: string; children: React.ReactNode; footer: React.ReactNode }) {
  return (
    <main className="auth-page">
      <Card className="auth-card">
        <div className="auth-head"><Link href="/"><Brand /></Link><h1>{title}</h1><p>{subtitle}</p></div>
        {children}
        <div className="auth-foot">{footer}</div>
      </Card>
    </main>
  );
}

