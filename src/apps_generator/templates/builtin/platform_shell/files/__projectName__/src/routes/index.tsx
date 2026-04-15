import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/useAuth";
import { useTenant } from "../tenants/useTenant";

export function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { currentTenant } = useTenant();

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">
        {t("welcome")}{user?.name ? `, ${user.name}` : ""}
      </h1>
      {currentTenant && (
        <p className="text-muted-foreground mb-6">
          {t("organization")}: <strong>{currentTenant.name}</strong>
        </p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="p-6 bg-card rounded-lg border">
          <h2 className="text-lg font-medium mb-2">{t("gettingStarted")}</h2>
          <p className="text-sm text-muted-foreground">
            {t("gettingStartedDesc")}
          </p>
        </div>
      </div>
    </div>
  );
}
