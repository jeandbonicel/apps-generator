{% if authProvider == "clerk" %}
import { useAuth as useClerkAuth, useUser } from "@clerk/clerk-react";
import type { User } from "../types";

export function useAuth() {
  const { isSignedIn, isLoaded, getToken, signOut } = useClerkAuth();
  const { user: clerkUser } = useUser();

  const user: User | null = clerkUser
    ? {
        id: clerkUser.id,
        email: clerkUser.primaryEmailAddress?.emailAddress ?? "",
        name: clerkUser.fullName ?? "",
        picture: clerkUser.imageUrl,
      }
    : null;

  return {
    isAuthenticated: !!isSignedIn,
    isLoading: !isLoaded,
    token: null as string | null, // use getToken() for async token retrieval
    getToken: () => getToken(),
    user,
    login: () => {}, // Clerk uses <SignInButton> component instead
    logout: () => signOut(),
  };
}
{% else %}
import { useAuth as useOidcAuth } from "react-oidc-context";
import type { User } from "../types";

export function useAuth() {
  const auth = useOidcAuth();

  const user: User | null = auth.user
    ? {
        id: auth.user.profile.sub,
        email: auth.user.profile.email ?? "",
        name: auth.user.profile.name ?? "",
        picture: auth.user.profile.picture,
      }
    : null;

  return {
    isAuthenticated: auth.isAuthenticated,
    isLoading: auth.isLoading,
    token: auth.user?.access_token ?? null,
    getToken: async () => auth.user?.access_token ?? null,
    user,
    login: () => auth.signinRedirect(),
    logout: () =>
      auth.signoutRedirect({ post_logout_redirect_uri: window.location.origin }),
  };
}
{% endif %}
