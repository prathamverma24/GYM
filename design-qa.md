# AthleteOS landing and auth - design QA

- Source visual truth: `E:\Dl\GYM\hero_ref.png`
- Generated hero plate: `apps/web/public/assets/landing-hero-bg-v2.png`
- Desktop implementation evidence: `E:\Dl\GYM\landing-final-prod.png`
- Compact implementation evidence: `E:\Dl\GYM\landing-mobile-final.png`
- Login implementation evidence: `E:\Dl\GYM\login-final-prod.png`
- Compact registration evidence: `E:\Dl\GYM\register-compact-prod.png`
- Desktop route and state: `/`, logged out
- Desktop viewport: 1717 x 916 CSS px at device scale factor 1
- Source pixels: 1717 x 916
- Implementation pixels: 1717 x 916

## Full-view comparison evidence

The reference and the final production capture were opened together at the same 1717 x 916 size. The implementation matches the reference's primary anchors: top navigation, left kicker and three-line headline, center athlete, right tilted analytics dashboard, trust row, and bottom six-item feature rail.

The new 1716 x 916 generated background was art-directed from the source and supplied gym image. It increases the athlete scale and moves the upper body to the center, while retaining dark copy space on the left and a controlled dashboard overlay area on the right. It contains no text, UI, logos, or watermarks.

## Focused checks

- Hero copy: line breaks, display weight, gradient emphasis, body width, CTA sizing, and trust-row rhythm match the reference.
- Dashboard: overview cards, workout list, macro ring, progress line, habit matrix, panel tilt, and bottom alignment match the reference hierarchy.
- Header and rail: five-link navigation, login/trial actions, six feature groups, icon treatment, dividers, and rail height were checked at full resolution.
- Login and registration: the generated gym plate fills the former empty background; the glass card remains readable and centered at desktop and compact widths.
- Responsive behavior: the 500 x 844 compact capture confirms working headline wrapping, stacked CTAs, a two-column trust grid, and a dashboard that stacks below the copy.

## Comparison history

### Pass 1 - blocked

- [P1] The original supplied athlete was too small and too far right compared with the reference.
  - Fix: generated a source-grounded background plate with a larger centered athlete and exact desktop aspect ratio.
- [P2] Login and registration used a mostly empty gradient background.
  - Fix: reused the generated photographic plate with layered contrast gradients and a glass treatment.
- [P1] Final onboarding could return to step one because the cached user/profile still said onboarding was incomplete.
  - Fix: update both caches from every save response, mark completion before navigation, and refresh the destination route.

### Pass 2 - passed

The same-size landing comparison has no actionable P0, P1, or P2 visual differences. Desktop login and compact registration have no clipped controls at their supported layout widths. The production build completes successfully.

## Functional verification

- Backend: 12 tests passed, including canonical mixed-case registration/login and the complete onboarding-to-login flow.
- Frontend: typecheck, lint, and 6 tests passed.
- Production build: all 22 routes generated successfully.
- Local preview: `/`, `/login`, and `/register` return HTTP 200.

## Findings

No actionable P0, P1, or P2 implementation findings remain.

## Follow-up deployment requirement

The Vercel project currently has no database environment variables. Production accounts require managed Postgres exposed as `DATABASE_URL`, `POSTGRES_URL`, `POSTGRES_PRISMA_URL`, `POSTGRES_URL_NON_POOLING`, or `NEON_DATABASE_URL`; the code now accepts all five names. The temporary `/tmp` SQLite fallback is not durable across serverless instances.

final result: passed
