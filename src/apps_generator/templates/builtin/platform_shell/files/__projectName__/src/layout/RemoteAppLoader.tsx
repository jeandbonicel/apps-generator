{% raw %}
import React, { Suspense } from "react";
import { useTranslation } from "react-i18next";
import { loadRemote } from "@module-federation/enhanced/runtime";

interface RemoteAppLoaderProps {
  remoteName: string;
  activePage?: string;
  basePath?: string;
}

const moduleCache: Record<string, React.LazyExoticComponent<React.ComponentType<{ activePage?: string; basePath?: string }>>> = {};

function getRemoteComponent(remoteName: string) {
  if (!moduleCache[remoteName]) {
    moduleCache[remoteName] = React.lazy(async () => {
      const mod = await loadRemote<{ default: React.ComponentType<{ activePage?: string; basePath?: string }> }>(`${remoteName}/App`);
      if (!mod) throw new Error(`Failed to load remote '${remoteName}/App'`);
      return mod;
    });
  }
  return moduleCache[remoteName];
}

export function RemoteAppLoader({ remoteName, activePage, basePath }: RemoteAppLoaderProps) {
  const { t } = useTranslation();
  const RemoteComponent = getRemoteComponent(remoteName);

  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">{t("loadingModule")}</p>
        </div>
      }
    >
      <RemoteComponent activePage={activePage} basePath={basePath} />
    </Suspense>
  );
}
{% endraw %}
