// Analysis, /analysis/ (IA_SPEC.md 4.3): three columns. Left, the source
// register and the ranked evidence trace; centre, the module output for the
// selected tab; right, always about the case — clearance, the route frontier,
// capital structure, armed triggers.
import { Capital } from "./Capital";
import { Clearance, Frontier } from "./Clearance";
import { EvidenceTrace } from "./EvidenceTrace";
import { ModuleOutput } from "./ModuleOutput";
import { SourceRegister } from "./SourceRegister";
import type { ViewProps } from "@/app/views";

export function AnalysisSection({ document, tab }: ViewProps<"analysis">) {
  const { chrome, body } = document;
  const activeTab = chrome.tabs.find((entry) => entry.id === tab) ?? chrome.tabs[0] ?? null;
  const module =
    body.modules.find((entry) => entry.module_id === activeTab?.cp) ?? body.modules[0] ?? null;
  const runState = chrome.rail.find((entry) => entry.section === "run")?.state ?? null;
  return (
    <div className="cols three" data-analysis>
      <div className="col left">
        <SourceRegister rows={body.register} />
        <EvidenceTrace rows={body.trace} />
      </div>
      <div
        className="col centre"
        role="tabpanel"
        id={activeTab ? `view-${activeTab.id}` : undefined}
        aria-labelledby={activeTab ? `tab-${activeTab.id}` : undefined}
      >
        <ModuleOutput module={module} body={body} />
      </div>
      <div className="col right">
        <Clearance clearance={body.clearance} />
        <Frontier items={body.frontier} runState={runState} />
        <Capital tranches={body.capital} triggers={body.triggers} />
      </div>
    </div>
  );
}
