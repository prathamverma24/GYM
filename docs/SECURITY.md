# Security Baseline

- Opaque, revocable sessions; HTTP-only/SameSite cookie; Secure in production.
- Versioned PBKDF2 password hashing with constant-time verification.
- Ownership checks on every athlete resource.
- Pydantic request validation, bounded search/history parameters and generic recovery responses.
- No password, session token, raw image, meal note or sensitive body payload logging.
- Raw image storage is off by default; future objects must be private and signed.
- Account export/deletion and password-reset tokens are auditable/idempotent work items for production hardening.

Run an OWASP ASVS/API Security review and production DAST before launch. The current application is an engineering MVP, not a completed legal/security certification.

