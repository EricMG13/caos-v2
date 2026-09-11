// The three hooks and the two label maps the workspace exports. A hook is
// reached by rendering something that calls it, so the section suites exercise
// all three without naming any — which is what left their failure modes
// untested: `useLedger` outside its provider, `useEvidence` outside its
// provider, and a tail opened where `EventSource` does not exist.
import { act, fireEvent, render, screen } from "@testing-library/react";
import { useRef, useState } from "react";
import { LedgerProvider, useLedger } from "@/app/ledger";
import { SECTION_ABBREVIATIONS, SECTION_LABELS } from "@/app/sections";
import { openTail } from "@/app/sse";
import { useModalA11y } from "@/ds/use-modal-a11y";
import { useEvidence } from "@/evidence/EvidenceContext";
import { SECTIONS } from "@/wire/shared";

describe("every section has a word and an abbreviation", () => {
  test("both maps cover the nine, and the strip rail's is one word each", () => {
    expect(Object.keys(SECTION_LABELS).sort()).toEqual([...SECTIONS].sort());
    expect(Object.keys(SECTION_ABBREVIATIONS).sort()).toEqual([...SECTIONS].sort());
    for (const section of SECTIONS) {
      expect(SECTION_ABBREVIATIONS[section]).toHaveLength(2);
      expect(SECTION_LABELS[section]).not.toContain(" ");
    }
  });
});

describe("a hook outside its provider says so rather than rendering nothing", () => {
  function Reads() {
    useLedger();
    return <span>read</span>;
  }

  test("useLedger throws outside a LedgerProvider", () => {
    // The provider is what holds it; silently returning an empty ledger would
    // draw a section whose figures are missing rather than absent.
    expect(() => render(<Reads />)).toThrow(/useLedger outside a LedgerProvider/);
  });

  test("useLedger inside one renders", () => {
    render(
      <LedgerProvider>
        <Reads />
      </LedgerProvider>,
    );
    expect(screen.getByText("read")).toBeInTheDocument();
  });

  test("useEvidence outside a provider opens nothing and holds no chip", () => {
    // Deliberately the other answer: the drawer belongs to the page it was
    // opened on, so a component that asks for it off-page gets a context that
    // does nothing rather than an exception that blanks the section.
    function AsksOffPage() {
      const evidence = useEvidence();
      return <span>{String(evidence.activeChip)}</span>;
    }
    render(<AsksOffPage />);
    expect(screen.getByText("null")).toBeInTheDocument();
  });
});

describe("modal a11y returns focus to the opener it was given", () => {
  function Dialog({ onClose }: { onClose: () => void }) {
    const opener = useRef<HTMLButtonElement>(null);
    const [open, setOpen] = useState(false);
    return (
      <>
        <button ref={opener} onClick={() => setOpen(true)}>
          open
        </button>
        {open ? (
          <Panel opener={opener.current} onClose={() => (setOpen(false), onClose())} />
        ) : null}
      </>
    );
  }

  function Panel({ opener, onClose }: { opener: HTMLElement | null; onClose: () => void }) {
    const ref = useModalA11y<HTMLDivElement>(onClose, opener);
    return (
      <div ref={ref} role="dialog" aria-modal="true">
        <button>inside</button>
      </div>
    );
  }

  test("it locks the body while open and clears the lock on close", () => {
    const closed = vi.fn();
    const { unmount } = render(<Dialog onClose={closed} />);
    fireEvent.click(screen.getByText("open"));
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    // Cleared outright rather than restored from a captured value.
    expect(document.body.style.overflow).toBe("");
  });

  test("Escape closes the topmost overlay", () => {
    const closed = vi.fn();
    render(<Dialog onClose={closed} />);
    fireEvent.click(screen.getByText("open"));
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(closed).toHaveBeenCalledOnce();
  });
});

describe("the event tail", () => {
  test("openTail is a no-op where EventSource does not exist", () => {
    // Server-rendered or a browser without it: the workspace still draws, and
    // closing a tail that was never opened is not an error.
    const held = globalThis.EventSource;
    // @ts-expect-error -- removing a global the runtime declares
    delete globalThis.EventSource;
    try {
      const tail = openTail("/api/events", { onEvent: vi.fn(), onStale: vi.fn() });
      expect(() => tail.close()).not.toThrow();
    } finally {
      globalThis.EventSource = held;
    }
  });

  test("a named event refetches and authority_changed also marks the region stale", () => {
    const listeners = new Map<string, () => void>();
    class Fake {
      addEventListener(name: string, handler: () => void) {
        listeners.set(name, handler);
      }
      close() {}
    }
    const held = globalThis.EventSource;
    globalThis.EventSource = Fake as unknown as typeof EventSource;
    try {
      const onEvent = vi.fn();
      const onStale = vi.fn();
      openTail("/api/events", { onEvent, onStale });

      listeners.get("run_terminal")?.();
      expect(onEvent).toHaveBeenCalledWith("run_terminal");
      expect(onStale).not.toHaveBeenCalled();

      listeners.get("authority_changed")?.();
      expect(onStale).toHaveBeenCalledOnce();
    } finally {
      globalThis.EventSource = held;
    }
  });
});
