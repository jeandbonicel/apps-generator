{% if authProvider == "clerk" %}
{% raw %}
import { OrganizationSwitcher } from "@clerk/clerk-react";

export function TenantSwitcher() {
  return (
    <OrganizationSwitcher
      hidePersonal={true}
      afterSelectOrganizationUrl="/"
      appearance={{
        elements: {
          rootBox: "flex items-center",
          organizationSwitcherTrigger:
            "px-3 py-1.5 text-sm font-medium bg-gray-100 rounded-md hover:bg-gray-200",
        },
      }}
    />
  );
}
{% endraw %}
{% else %}
import { useState, useRef, useEffect } from "react";
import { useTenant } from "./useTenant";

export function TenantSwitcher() {
  const { tenants, currentTenant, switchTenant, isLoading } = useTenant();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (isLoading) {
    return <span className="text-sm text-gray-400">Loading tenants...</span>;
  }

  if (tenants.length <= 1) {
    return currentTenant ? (
      <span className="text-sm font-medium">{currentTenant.name}</span>
    ) : null;
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium bg-gray-100 rounded-md hover:bg-gray-200"
      >
        <span>{currentTenant?.name ?? "Select organization"}</span>
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {isOpen && (
        <div className="absolute left-0 z-50 mt-1 w-56 bg-white border border-gray-200 rounded-md shadow-lg">
          {tenants.map((tenant) => (
            <button
              key={tenant.id}
              onClick={() => {
                switchTenant(tenant.id);
                setIsOpen(false);
              }}
              className={`w-full px-4 py-2 text-left text-sm hover:bg-accent ${
                tenant.id === currentTenant?.id
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-foreground"
              }`}
            >
              {tenant.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
{% endif %}
