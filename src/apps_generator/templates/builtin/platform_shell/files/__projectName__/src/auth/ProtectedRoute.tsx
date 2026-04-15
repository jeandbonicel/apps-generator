{% if authProvider == "clerk" %}
import { useAuth, SignInButton } from "@clerk/clerk-react";
import { Outlet } from "@tanstack/react-router";

export function ProtectedRoute() {
  const { isSignedIn, isLoaded } = useAuth();

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4">
        <h1 className="text-2xl font-semibold">{{ projectTitle or projectName }}</h1>
        <p>Please sign in to continue.</p>
        <SignInButton mode="modal">
          <button className="px-4 py-2 text-primary-foreground bg-primary rounded hover:bg-primary/90">
            Sign In
          </button>
        </SignInButton>
      </div>
    );
  }

  return <Outlet />;
}
{% else %}
import { useAuth } from "react-oidc-context";
import { Outlet } from "@tanstack/react-router";

export function ProtectedRoute() {
  const auth = useAuth();

  if (auth.isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  if (auth.error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Authentication error: {auth.error.message}</p>
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4">
        <h1 className="text-2xl font-semibold">{{ projectTitle or projectName }}</h1>
        <p>Please sign in to continue.</p>
        <button
          onClick={() => auth.signinRedirect()}
          className="px-4 py-2 text-primary-foreground bg-primary rounded hover:bg-primary/90"
        >
          Sign In
        </button>
      </div>
    );
  }

  return <Outlet />;
}
{% endif %}
