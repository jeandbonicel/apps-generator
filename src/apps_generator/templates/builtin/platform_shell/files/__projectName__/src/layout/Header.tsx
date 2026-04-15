import { TenantSwitcher } from "../tenants/TenantSwitcher";
import { LanguageSwitcher } from "../i18n/LanguageSwitcher";
{% if authProvider == "clerk" %}
import { UserButton } from "@clerk/clerk-react";
{% else %}
import { useAuth } from "../auth/useAuth";
{% endif %}

export function Header() {
{% if authProvider != "clerk" %}
  const { user, logout } = useAuth();
{% endif %}

  return (
    <header className="flex items-center justify-between h-14 px-4 bg-background border-b shrink-0">
      <div className="flex items-center gap-4">
        <span className="text-lg font-semibold">{{ projectTitle or projectName }}</span>
        <TenantSwitcher />
      </div>
      <div className="flex items-center gap-3">
        <LanguageSwitcher />
{% if authProvider == "clerk" %}
        <UserButton afterSignOutUrl="/" />
{% else %}
        {user && (
          <span className="text-sm text-muted-foreground">{user.name || user.email}</span>
        )}
        <button
          onClick={logout}
          className="px-3 py-1.5 text-sm text-muted-foreground border rounded-md hover:bg-accent"
        >
          Sign Out
        </button>
{% endif %}
      </div>
    </header>
  );
}
