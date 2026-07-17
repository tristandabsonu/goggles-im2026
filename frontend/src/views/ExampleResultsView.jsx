import { useRef, useState } from "react";

import { ResultPanel } from "../components/Feedback";
import exampleResults from "../data/example-results.json";

export default function ExampleResultsView() {
  const examples = exampleResults.examples;
  const [selectedId, setSelectedId] = useState(examples[0].id);
  const tabRefs = useRef([]);
  const selected =
    examples.find((example) => example.id === selectedId) || examples[0];

  function selectTab(index, focus = false) {
    const wrappedIndex = (index + examples.length) % examples.length;
    setSelectedId(examples[wrappedIndex].id);
    if (focus) {
      window.requestAnimationFrame(() => tabRefs.current[wrappedIndex]?.focus());
    }
  }

  function handleTabKeyDown(event, index) {
    const nextIndex = {
      ArrowRight: index + 1,
      ArrowLeft: index - 1,
      Home: 0,
      End: examples.length - 1,
    }[event.key];

    if (nextIndex === undefined) return;
    event.preventDefault();
    selectTab(nextIndex, true);
  }

  const proposalTabs = (
    <div
      className="example-tabs"
      role="tablist"
      aria-label="Synthetic proposal results"
    >
      {examples.map((example, index) => {
        const active = example.id === selected.id;
        return (
          <button
            key={example.id}
            ref={(element) => {
              tabRefs.current[index] = element;
            }}
            id={`example-tab-${example.id}`}
            type="button"
            role="tab"
            aria-selected={active}
            aria-controls="example-panel"
            tabIndex={active ? 0 : -1}
            className={active ? "example-tab active" : "example-tab"}
            onClick={() => selectTab(index)}
            onKeyDown={(event) => handleTabKeyDown(event, index)}
          >
            {example.tab_label}
          </button>
        );
      })}
    </div>
  );

  return (
    <main id="main-content" className="examples-page" tabIndex={-1}>
      <section className="examples-hero">
        <div className="examples-hero-inner">
          <span className="eyebrow">Example results</span>
          <h1>
            See GOGgles results
            <br />
            without the wait.
          </h1>
          <p>
            Explore six captured runs of the supported checks on synthetic
            proposals, rendered exactly like the Assessor results on the homepage.
          </p>
        </div>
      </section>

      <div className="examples-layout">
        <div className="example-notes">
          <aside className="example-note example-speed-note">
            <span className="example-note-label">Why these are preloaded</span>
            <strong>Live checks usually take 60–180 seconds.</strong>
            <p>
              These captured runs load immediately. You can run the same fictional
              PDFs from the homepage when you want to see a fresh check.
            </p>
            <a href="/#try-it-now">Run a live check</a>
          </aside>
          <aside className="example-note example-variability-note">
            <span className="example-note-label">About model variability</span>
            <strong>A fresh run may not produce identical results.</strong>
            <p>
              Generative answers can vary in wording and classification, and live
              runs may use a different configured model. Every finding remains
              review assistance: a person must verify the cited source, correct the
              output where needed and retain responsibility for all decisions.
            </p>
          </aside>
        </div>

        <div className="example-browser">
          <ResultPanel
            result={selected.result}
            controls={proposalTabs}
            contentProps={{
              id: "example-panel",
              className: "example-tab-panel",
              role: "tabpanel",
              "aria-labelledby": `example-tab-${selected.id}`,
              tabIndex: 0,
            }}
          />
        </div>
      </div>
    </main>
  );
}
