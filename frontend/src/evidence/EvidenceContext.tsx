// One evidence drawer and one passport for the whole workspace. Openers are
// passed from the click that opened them; there is no second inspector.
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { MetricPassport } from "./MetricPassport";
import type { Citation, Passport } from "@/wire";

interface Evidence {
  openCitation(citation: Citation, opener: HTMLElement): void;
  openPassport(passport: Passport, opener: HTMLElement): void;
  activeChip: string | null;
}

const Context = createContext<Evidence>({
  openCitation() {},
  openPassport() {},
  activeChip: null,
});

export function useEvidence(): Evidence {
  return useContext(Context);
}

interface Open<T> {
  subject: T;
  opener: HTMLElement;
}

export function EvidenceProvider({ children }: { children: ReactNode }) {
  const [citation, setCitation] = useState<Open<Citation> | null>(null);
  const [passport, setPassport] = useState<Open<Passport> | null>(null);
  const openCitation = useCallback(
    (subject: Citation, opener: HTMLElement) => setCitation({ subject, opener }),
    [],
  );
  const openPassport = useCallback(
    (subject: Passport, opener: HTMLElement) => setPassport({ subject, opener }),
    [],
  );
  const value = useMemo(
    () => ({ openCitation, openPassport, activeChip: citation?.subject.chip ?? null }),
    [openCitation, openPassport, citation],
  );
  return (
    <Context.Provider value={value}>
      {children}
      {passport ? (
        <MetricPassport
          passport={passport.subject}
          opener={passport.opener}
          onClose={() => setPassport(null)}
        />
      ) : null}
      {citation ? (
        <EvidenceDrawer
          citation={citation.subject}
          opener={citation.opener}
          onClose={() => setCitation(null)}
        />
      ) : null}
    </Context.Provider>
  );
}
