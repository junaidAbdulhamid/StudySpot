export function authError(error: unknown): string {
  const code =
    error && typeof error === "object" && "code" in error
      ? String(error.code)
      : "";
  if (code === "invalid_credentials")
    return "We couldn’t sign you in. Check your email and password.";
  if (code === "email_not_confirmed")
    return "Check your inbox to confirm your email before signing in.";
  if (code === "user_already_exists" || code === "email_exists")
    return "An account already uses this email. Try signing in.";
  if (code === "weak_password")
    return "Choose a stronger password that meets the account requirements.";
  if (
    code === "over_request_rate_limit" ||
    code === "over_email_send_rate_limit"
  )
    return "Too many attempts. Please wait a little and try again.";
  if (error instanceof Error && error.message === "AUTH_CONFIGURATION")
    return "Sign-in needs Supabase configuration. See the setup guide.";
  if (error instanceof Error && error.message === "OAUTH_CANCELLED")
    return "Sign-in was canceled. You can try again whenever you’re ready.";
  return "We couldn’t complete that request. Check your connection and try again.";
}
