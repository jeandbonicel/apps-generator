import { Outlet } from "@tanstack/react-router";
import { Header } from "./Header";
import { AppTabs } from "./AppTabs";

export function AppShell() {
  return (
    <div className="flex flex-col h-screen">
      <Header />
      <AppTabs />
      <main className="flex-1 overflow-auto bg-muted/40">
        <Outlet />
      </main>
    </div>
  );
}
