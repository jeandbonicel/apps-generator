{% if authProvider == "clerk" %}
// Clerk auth is handled via ClerkProvider in main.tsx.
// This file re-exports Clerk components for use throughout the app.
export {
  SignedIn,
  SignedOut,
  SignInButton,
  UserButton,
} from "@clerk/clerk-react";
{% else %}
import { AuthProvider as OidcAuthProvider } from "react-oidc-context";
import type { WebStorageStateStore } from "oidc-client-ts";
import type { ReactNode } from "react";

const oidcConfig = {
  authority: "{{ oidcAuthority }}",
  client_id: "{{ oidcClientId }}",
  redirect_uri: window.location.origin,
  post_logout_redirect_uri: window.location.origin,
  scope: "{{ oidcScopes }}",
  response_type: "code",
  automaticSilentRenew: true,
  userStore: new (
    await import("oidc-client-ts")
  ).WebStorageStateStore({
    store: window.localStorage,
  }) as WebStorageStateStore,
};

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  return <OidcAuthProvider {...oidcConfig}>{children}</OidcAuthProvider>;
}
{% endif %}
