import { useEffect, useRef, useState } from "react";

import assessorA from "../assets/how-it-works/assessor_viewA.jpg";
import assessorB from "../assets/how-it-works/assessor_viewB.jpg";
import assessorC from "../assets/how-it-works/assessor_viewC.jpg";
import writerA from "../assets/how-it-works/writer_viewA.jpg";
import writerB from "../assets/how-it-works/writer_viewB.jpg";
import writerC from "../assets/how-it-works/writer_viewC.jpg";

const FRAME_INTERVAL_MS = 1400;

const VIEWS = [
  {
    id: "assessor",
    label: "Assessor",
    description: "Review a submitted proposal",
    steps: [
      {
        title: "Attach the documents",
        body: "Keep or replace the preloaded GOG, Application Form and supporting PDFs, then select a synthetic Grant Proposal or upload your own test proposal.",
      },
      {
        title: "Start the review",
        body: "Press “Check grant proposal”. GOGgles first identifies the supported proposal sections, then reviews each one in sequence.",
      },
      {
        title: "Verify and decide",
        body: "Read the comments and suggested actions, open the cited sources, correct anything that needs correcting and make the assessment decision yourself.",
      },
    ],
    backend:
      "Pass 1 extracts the supported sections from the proposal. Pass 2 checks those sections one at a time against the complete labelled document bundle.",
    figureLabel:
      "Assessor backend workflow: proposal-section extraction followed by sequential section reviews against the full document bundle.",
    progressLabel: "Reviewing assessable section",
    frames: [assessorA, assessorB, assessorC],
  },
  {
    id: "writer",
    label: "Writer",
    description: "Check a draft before submitting",
    steps: [
      {
        title: "Write the draft",
        body: "Complete the form in Writer view. Administrative details stay in the browser; only answers marked “AI check” are prepared for review.",
      },
      {
        title: "Check the marked fields",
        body: "Press “Check assessable fields”. GOGgles sends each marked answer in its own call with the applicant-facing guidance documents.",
      },
      {
        title: "Write the change",
        body: "Use the inline comment, suggested action and source to improve the field. GOGgles gives guidance; you remain the author.",
      },
    ],
    backend:
      "Writer view needs no proposal upload and no extraction pass. Each marked field is checked by itself, so another draft answer cannot silently fill in a gap.",
    figureLabel:
      "Writer backend workflow: isolated draft fields reviewed sequentially against applicant-facing guidance documents.",
    progressLabel: "Reviewing draft field",
    frames: [writerA, writerB, writerC],
  },
];

function AnimatedDiagram({ view, reduceMotion }) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    setFrame(0);
    if (reduceMotion) return undefined;

    const timer = window.setInterval(() => {
      setFrame((current) => (current + 1) % view.frames.length);
    }, FRAME_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [reduceMotion, view]);

  return (
    <figure className="how-diagram" aria-label={view.figureLabel}>
      <div className="how-diagram-scroll">
        <div className="how-diagram-stage">
          {view.frames.map((source, index) => (
            <img
              key={source}
              className={index === frame ? "is-active" : ""}
              src={source}
              alt=""
              aria-hidden="true"
            />
          ))}
        </div>
      </div>
      <figcaption>
        <span>{view.progressLabel}</span>
        <span className="how-frame-controls" aria-label="Diagram frame">
          {view.frames.map((source, index) => (
            <button
              key={source}
              type="button"
              className={index === frame ? "is-active" : ""}
              aria-label={`Show section ${String.fromCharCode(65 + index)}`}
              aria-pressed={index === frame}
              onClick={() => setFrame(index)}
            >
              {String.fromCharCode(65 + index)}
            </button>
          ))}
        </span>
      </figcaption>
    </figure>
  );
}

export default function WorkflowSequence() {
  const [viewId, setViewId] = useState("assessor");
  const [reduceMotion, setReduceMotion] = useState(false);
  const tabRefs = useRef([]);
  const activeView = VIEWS.find((view) => view.id === viewId) || VIEWS[0];

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setReduceMotion(preference.matches);
    updatePreference();
    preference.addEventListener("change", updatePreference);
    return () => preference.removeEventListener("change", updatePreference);
  }, []);

  function selectTab(index, focus = false) {
    const wrapped = (index + VIEWS.length) % VIEWS.length;
    setViewId(VIEWS[wrapped].id);
    if (focus) {
      window.requestAnimationFrame(() => tabRefs.current[wrapped]?.focus());
    }
  }

  function handleTabKeyDown(event, index) {
    const nextIndex = {
      ArrowRight: index + 1,
      ArrowLeft: index - 1,
      Home: 0,
      End: VIEWS.length - 1,
    }[event.key];

    if (nextIndex === undefined) return;
    event.preventDefault();
    selectTab(nextIndex, true);
  }

  return (
    <section className="how-process" aria-labelledby="how-process-title">
      <div className="how-process-intro">
        <h2 id="how-process-title">Use GOGgles in three steps.</h2>
        <p>
          Choose the view that matches where you are in the application process.
        </p>
      </div>

      <div className="how-process-tabs" role="tablist" aria-label="GOGgles views">
        {VIEWS.map((view, index) => {
          const active = view.id === viewId;
          return (
            <button
              key={view.id}
              ref={(element) => {
                tabRefs.current[index] = element;
              }}
              id={`how-process-tab-${view.id}`}
              type="button"
              role="tab"
              aria-selected={active}
              aria-controls="how-process-panel"
              tabIndex={active ? 0 : -1}
              className={active ? "is-active" : ""}
              onClick={() => selectTab(index)}
              onKeyDown={(event) => handleTabKeyDown(event, index)}
            >
              <span>{view.label}</span>
              <small>{view.description}</small>
            </button>
          );
        })}
      </div>

      <div
        id="how-process-panel"
        className="how-process-panel"
        role="tabpanel"
        aria-labelledby={`how-process-tab-${viewId}`}
        tabIndex={0}
      >
        <ol className="how-user-steps">
          {activeView.steps.map((step, index) => (
            <li key={step.title}>
              <span>{index + 1}</span>
              <strong>{step.title}</strong>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>

        <div className="how-backend-intro">
          <h3>What happens after you click</h3>
          <p>{activeView.backend}</p>
        </div>

        <AnimatedDiagram view={activeView} reduceMotion={reduceMotion} />

        <div className="how-dev-cta">
          <p>Model choice, request flow and architecture trade-offs.</p>
          <a href="/for-devs">
            For the devs <span aria-hidden="true">→</span>
          </a>
        </div>
      </div>
    </section>
  );
}
