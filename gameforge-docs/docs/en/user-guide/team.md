# Team

Studio-tier organizations let you invite teammates and share seats.

## Requirements

- An active **Studio** (or higher) plan, or on-prem `FORCE_PLAN=enterprise`
- Access to the **Team** page in the UI

## Flow

1. Upgrade to Studio (or enable billing/on-prem plan).
2. An organization is created (or create via API `POST /api/v1/orgs`).
3. Invite members by email.
4. Invitees open the accept-invite link and join.

## Roles

Org membership roles control who can invite and manage the studio. Admins of the platform (`UserRole.ADMIN`) can manage users globally — see [Admin → Users](../admin-guide/users.md).

## Email

Invites and password resets need a real mail provider in production (`EMAIL_PROVIDER=resend` or `smtp`). With `console`, messages only appear in API logs (local/dev).
