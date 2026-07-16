export function SourceList({ sources = [] }) {
  if (!sources.length) return null;

  return (
    <div className="sources">
      {sources.map((source, index) => (
        <details key={`${source.document}-${source.reference}-${index}`}>
          <summary>
            {source.document} · {source.reference}
          </summary>
          {source.excerpt && <p>“{source.excerpt}”</p>}
        </details>
      ))}
    </div>
  );
}

export function Finding({ finding }) {
  return (
    <div className="finding">
      <p>{finding.comment}</p>
      {finding.suggested_action && (
        <p className="action">
          <strong>Human action:</strong> {finding.suggested_action}
        </p>
      )}
      <SourceList sources={finding.sources} />
    </div>
  );
}

export function ClassificationBadge({ value }) {
  const labels = {
    in_scope: "No issue identified",
    out_of_scope: "Out of scope",
    vague: "Needs detail",
    clarified_elsewhere: "Clarified elsewhere",
  };

  return (
    <span className={`status status-${value}`}>{labels[value] || value}</span>
  );
}

export function ClarificationEvidence({ evidence }) {
  if (!evidence) return null;

  const pages = evidence.source_pages?.length
    ? ` · page ${evidence.source_pages.join(", ")}`
    : "";

  return (
    <div className="clarification-evidence">
      <strong>Verified elsewhere:</strong> {evidence.source_section}
      {pages}
      <blockquote>“{evidence.excerpt}”</blockquote>
    </div>
  );
}

function BudgetItemDetails({ item }) {
  return (
    <div className="budget-item-details">
      <p className="budget-item-comment">
        {item.comment || "No comment needed for this check."}
      </p>
      {item.suggested_action && (
        <p className="action">{item.suggested_action}</p>
      )}
      <ClarificationEvidence evidence={item.clarification_evidence} />
      <SourceList sources={item.sources} />
    </div>
  );
}

function BudgetTable({ items }) {
  return (
    <>
      <div className="table-wrap budget-table-view">
        <table>
          <caption className="visually-hidden">Budget item checks</caption>
          <thead>
            <tr>
              <th scope="col">Budget item</th>
              <th scope="col">Amount</th>
              <th scope="col">Check</th>
              <th scope="col">Comment</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <tr key={`${item.item}-${index}`}>
                <td>{item.item}</td>
                <td>{item.amount}</td>
                <td>
                  <ClassificationBadge value={item.classification} />
                </td>
                <td>
                  <BudgetItemDetails item={item} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="budget-card-list" aria-label="Budget item checks">
        {items.map((item, index) => (
          <li className="budget-result-card" key={`${item.item}-${index}`}>
            <dl>
              <div className="budget-card-field">
                <dt>Budget item</dt>
                <dd className="budget-card-item">{item.item}</dd>
              </div>
              <div className="budget-card-field">
                <dt>Amount</dt>
                <dd>{item.amount}</dd>
              </div>
              <div className="budget-card-field">
                <dt>Check</dt>
                <dd>
                  <ClassificationBadge value={item.classification} />
                </dd>
              </div>
              <div className="budget-card-field budget-card-comment">
                <dt>Comment</dt>
                <dd>
                  <BudgetItemDetails item={item} />
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}

function SectionCard({ section }) {
  const isEmpty =
    !section.findings.length &&
    !section.budget_items.length &&
    !section.error;

  return (
    <article className="result-card">
      <div className="result-heading">
        <div>
          <span className="eyebrow">Assessed section</span>
          <h3>{section.header}</h3>
        </div>
        <span className="section-type">
          {section.type.replaceAll("_", " ")}
        </span>
      </div>
      {section.error && <div className="error-box">{section.error}</div>}
      {section.findings.map((finding, index) => (
        <Finding key={index} finding={finding} />
      ))}
      {!!section.budget_items.length && (
        <BudgetTable items={section.budget_items} />
      )}
      {isEmpty && section.has_threshold_flag && (
        <p className="review-message">
          This section raised the human-review flag shown above.
        </p>
      )}
      {isEmpty && !section.has_threshold_flag && (
        <p className="clear-message">No issue identified by this check.</p>
      )}
    </article>
  );
}

function ExtractedFieldsPanel({ sections = [], assessedSectionIds }) {
  if (!sections.length) return null;

  return (
    <section className="extraction-panel">
      <div className="extraction-heading">
        <div>
          <span className="eyebrow">Pass 1 · Proposal structure</span>
          <h3>Extracted proposal sections</h3>
        </div>
        <span className="extraction-count">{sections.length} fields</span>
      </div>
      <p>
        GOGgles identified these applicant answers before running its supported
        checks. Sections marked “Not assessed” are shown only for context and
        transparency.
      </p>
      <div className="extracted-fields">
        {sections.map((section, index) => (
          <details className="extracted-field" key={`${section.id}-${index}`}>
            <summary>
              <span className="extracted-order">{index + 1}</span>
              <span className="extracted-name">
                <strong>{section.header}</strong>
                <small>
                  {section.type.replaceAll("_", " ")} ·{" "}
                  {section.source_pages?.length
                    ? `page ${section.source_pages.join(", ")}`
                    : "page unavailable"}
                  {" · "}
                  {assessedSectionIds.has(section.id)
                    ? "Supported check run"
                    : "Not assessed"}
                </small>
              </span>
              <span className="view-field">View extracted text</span>
            </summary>
            <div className="extracted-text">{section.text}</div>
          </details>
        ))}
      </div>
    </section>
  );
}

function ResultBody({ result }) {
  const assessedSectionIds = new Set(
    result.sections.map((section) => section.id),
  );

  return (
    <>
      <ExtractedFieldsPanel
        sections={result.extracted_sections}
        assessedSectionIds={assessedSectionIds}
      />
      {!!result.threshold_flags.length && (
        <div className="thresholds">
          {result.threshold_flags.map((flag, index) => (
            <div className="threshold" key={`${flag.code}-${index}`}>
              <span className="status status-review">Human review</span>
              <h3>Funding stream needs attention</h3>
              <p>{flag.comment}</p>
              <p className="action">
                <strong>Human action:</strong> {flag.suggested_action}
              </p>
              <SourceList sources={flag.sources} />
            </div>
          ))}
        </div>
      )}
      <div className="result-list">
        {result.sections.map((section) => (
          <SectionCard section={section} key={section.id} />
        ))}
      </div>
    </>
  );
}

export function ResultPanel({
  result,
  controls = null,
  contentProps = null,
}) {
  const body = <ResultBody result={result} />;

  return (
    <section className="results" aria-live="polite">
      <div className="section-intro">
        <span className="eyebrow">Review assistance</span>
        <h2>Check results</h2>
        <p>
          Every result is a comment for a person to verify, not an assessment
          decision. GOGgles cannot stop or auto-reject an application.
        </p>
      </div>
      {controls}
      {contentProps ? <div {...contentProps}>{body}</div> : body}
    </section>
  );
}
