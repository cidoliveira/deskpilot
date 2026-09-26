import { useEffect } from "react";

/** Browser tab title: "<page> · DeskPilot", so several open tabs stay distinguishable. */
export function usePageTitle(title: string | undefined) {
  useEffect(() => {
    document.title = title ? `${title} · DeskPilot` : "DeskPilot";
  }, [title]);
}
