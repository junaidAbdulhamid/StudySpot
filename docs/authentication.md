# StudySpot authentication

StudySpot uses Supabase Auth for passwords, OAuth identities, access tokens, refresh tokens, and email
delivery. FastAPI owns the application profile, onboarding flag, preferences, and favorites. Private API
routes resolve the StudySpot user from a Supabase-verified bearer token, never a client-provided user ID.

## Environment and Supabase

Copy both `.env.example` files. Set the same Supabase project URL and public anon/publishable key in the
backend and mobile environments. Only the public key belongs in `EXPO_PUBLIC_*`. Never put a service-role
key, JWT secret, or database credential in the mobile app.

In Supabase Authentication → URL Configuration, add `studyspot://auth/callback` to Redirect URLs and set
the deployed web app's HTTPS URL as Site URL. Enable Email, decide whether confirmation is required, and
configure production SMTP before release. The native identifiers are `edu.studyspot.mobile` for iOS and
Android; the Expo scheme is `studyspot`.

## Google

Configure Google's OAuth consent screen and create a Web OAuth client. Add the exact callback shown by
Supabase's Google provider settings, normally
`https://<project-ref>.supabase.co/auth/v1/callback`, as an authorized redirect URI. Put the Google client
ID and secret in Supabase, never in this repository. Add the deployed web origin to Google when web login
is enabled. The app says “Continue with Google”; it does not claim university SSO.

Sign in with Apple was deliberately removed — it required a paid Apple Developer account this project
doesn't have. Email/password and Google cover sign-in for now; re-adding Apple later means restoring the
button in `login.tsx`, the `"apple"` provider type in `AuthProvider.oauth`, and enabling/configuring the
provider in Supabase.

## Sessions, verification, and routing

Native Supabase session JSON is chunked into `expo-secure-store`; AsyncStorage stores only the intro flag
and notification preference. The API client attaches access tokens centrally, refreshes once after a 401,
and retries once. Provider/network outages preserve the session. FastAPI validates through the configured
Supabase `/auth/v1/user` endpoint, supporting legacy and rotated signing keys without trusting decoded JWT
claims locally.

Startup restores the session before rendering navigation, loads `/api/v1/me`, and routes incomplete users
to preference onboarding. Preference saving and `onboarding_completed` use one database transaction.
`AppStore` is keyed by provider subject, so logout and account switching discard all previous user state.

## Testing and deletion boundary

Playwright uses `backend/tests/e2e_auth.py`, a test-only GoTrue-shaped HTTP fixture exercised through the
real `supabase-js` client and backend verifier. Production has no mock-auth fallback.

`AccountService.delete_application_data` deletes the StudySpot row and cascades preferences and favorites.
A future public deletion endpoint must first use a privileged backend-only Supabase Admin integration to
revoke/delete the provider identity, then delete StudySpot data. The app does not claim provider-account
deletion is currently available; deleting only local data would allow the next valid login to recreate it.
