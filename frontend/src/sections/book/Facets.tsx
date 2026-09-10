// The left column of the book: facets as real checkbox groups, grouping keys
// as pressed pills, and the saved views with their scope labels.
import { useId } from "react";
import type { Facet, SavedView } from "@/wire/book";

const wordOf = (key: string) => key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ");

export function Facets({
  facets,
  checked,
  onToggle,
  groupingKeys,
  groupKey,
  onGroup,
  savedViews,
}: {
  facets: Facet[];
  checked: Record<string, ReadonlySet<string>>;
  onToggle: (facetKey: string, value: string) => void;
  groupingKeys: string[];
  groupKey: string;
  onGroup: (key: string) => void;
  savedViews: SavedView[];
}) {
  const groupLabelId = useId();
  return (
    <section className="pnl" data-facets>
      <header>
        <h2>Facets</h2>
        <span className="cp">FILTER · GROUP</span>
      </header>
      <div className="pb flush">
        <div className="facet" data-grouping>
          <div className="lbl" id={groupLabelId} style={{ marginBottom: 6 }}>
            Group rows by
          </div>
          <div className="pillrow" role="group" aria-labelledby={groupLabelId}>
            {groupingKeys.map((key) => (
              <button
                key={key}
                type="button"
                className="pill"
                aria-pressed={key === groupKey}
                data-group-key={key}
                onClick={() => onGroup(key)}
              >
                {wordOf(key)}
              </button>
            ))}
          </div>
        </div>
        {facets.map((facet) => (
          <fieldset key={facet.key} className="facet" data-facet={facet.key}>
            <legend>{facet.label}</legend>
            {facet.options.map((option) => (
              <label key={option.value} className="fopt">
                <input
                  type="checkbox"
                  checked={checked[facet.key]?.has(option.value) ?? option.on}
                  onChange={() => onToggle(facet.key, option.value)}
                  data-facet-option={option.value}
                />
                {option.value}
                {facet.key === "definition_set" && option.value === "Deviates" ? (
                  <span className="defmark" aria-hidden="true" />
                ) : null}
                <span className="n tabular">{option.count}</span>
              </label>
            ))}
          </fieldset>
        ))}
        <div className="facet" data-saved-views>
          <div className="lbl" style={{ marginBottom: 6 }}>
            Saved views
          </div>
          {savedViews.length ? (
            <ul className="plain">
              {savedViews.map((view) => (
                <li key={view.name} className="fopt" data-saved-view={view.name}>
                  <span>{view.name}</span>
                  <span className="n">
                    <span className="tag" data-scope={view.scope}>
                      {view.scope}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="note">No saved view.</div>
          )}
        </div>
      </div>
    </section>
  );
}
