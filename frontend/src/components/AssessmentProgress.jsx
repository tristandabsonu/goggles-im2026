export default function AssessmentProgress({
  progress,
  includeExtraction = true,
  itemLabel = "sections",
  preparingLabel = "Preparing section reviews",
  message = "This can take a few minutes. Keep this page open while GOGgles checks the supplied PDFs.",
}) {
  const extractionComplete = progress.phase !== "extracting";
  const stages = [
    ...(includeExtraction
      ? [
          {
            key: "extracting",
            label: "Extracting assessable sections",
            status: extractionComplete ? "complete" : "active",
          },
        ]
      : []),
    ...progress.sections.map((section, index) => {
      const position = index + 1;
      let status = "pending";
      if (progress.phase === "complete" || position < progress.current) {
        status = "complete";
      } else if (position === progress.current) {
        status = "active";
      }
      return {
        key: section.id,
        label: `Reviewing “${section.header}”`,
        status,
      };
    }),
  ];
  const activeStage = stages.find((stage) => stage.status === "active");

  return (
    <section className="assessment-progress" role="status" aria-live="polite">
      <div className="progress-heading">
        <div>
          <span className="eyebrow">Review in progress</span>
          <h3>
            {activeStage?.label ||
              (progress.phase === "complete"
                ? "Preparing results"
                : preparingLabel)}
          </h3>
        </div>
        {progress.sections.length > 0 && progress.phase !== "extracting" && (
          <span className="progress-count">
            {Math.min(progress.current, progress.sections.length)} of{" "}
            {progress.sections.length} {itemLabel}
          </span>
        )}
      </div>
      <p>{message}</p>
      <ol className="progress-stages">
        {stages.map((stage, index) => (
          <li
            className={`progress-stage is-${stage.status}`}
            key={stage.key}
            aria-current={stage.status === "active" ? "step" : undefined}
          >
            <span className="progress-marker" aria-hidden="true">
              {stage.status === "complete" ? (
                "✓"
              ) : stage.status === "active" ? (
                <span className="spinner" />
              ) : (
                index + 1
              )}
            </span>
            <span>{stage.label}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
