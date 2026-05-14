import { useEffect, useState, type ReactNode } from "react";

const WORKLIST_MOBILE_QUERY = "(max-width: 860px)";

function getIsMobileWorklist() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }

  return window.matchMedia(WORKLIST_MOBILE_QUERY).matches;
}

function useIsMobileWorklist() {
  const [isMobile, setIsMobile] = useState(getIsMobileWorklist);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const mediaQuery = window.matchMedia(WORKLIST_MOBILE_QUERY);
    const handleChange = () => setIsMobile(mediaQuery.matches);

    handleChange();
    mediaQuery.addEventListener("change", handleChange);

    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  return isMobile;
}

export function WorklistEmptyState({
  description,
  eyebrow,
  title,
}: {
  description: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <div className="empty-state">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p className="empty-state-description">{description}</p>
    </div>
  );
}

export function WorklistErrorState({ children }: { children: ReactNode }) {
  return (
    <div className="error-panel" role="alert">
      {children}
    </div>
  );
}

export function WorklistSkeleton({ label }: { label: string }) {
  return (
    <div aria-label={label} className="worklist-skeleton" role="status">
      {Array.from({ length: 3 }).map((_, index) => (
        <div className="worklist-skeleton-card" key={index}>
          <span className="worklist-skeleton-line wide" />
          <span className="worklist-skeleton-line medium" />
          <span className="worklist-skeleton-line narrow" />
        </div>
      ))}
    </div>
  );
}

export function ResponsiveWorklistFrame({
  desktop,
  empty,
  isEmpty,
  isPending,
  mobile,
  skeletonLabel,
}: {
  desktop: ReactNode;
  empty: ReactNode;
  isEmpty: boolean;
  isPending: boolean;
  mobile: ReactNode;
  skeletonLabel: string;
}) {
  const isMobile = useIsMobileWorklist();

  return (
    <div className="table-frame">
      {isPending ? (
        <WorklistSkeleton label={skeletonLabel} />
      ) : isEmpty ? (
        empty
      ) : isMobile ? (
        mobile
      ) : (
        desktop
      )}
    </div>
  );
}
