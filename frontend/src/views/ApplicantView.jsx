import { useMemo, useRef, useState } from "react";

import { checkApplicant, fetchDemoFile } from "../api";
import AssessmentProgress from "../components/AssessmentProgress";
import { PreviewModal } from "../components/Documents";
import {
  ClarificationEvidence,
  ClassificationBadge,
  Finding,
  SourceList,
} from "../components/Feedback";

const DEFAULT_ROWS = [
  {
    item: "First Nations storytelling",
    amount: "600",
  },
  { item: "Event delivery", amount: "5500" },
  { item: "Workshop costs", amount: "1000" },
  { item: "NAIDOC T-shirts for participants", amount: "1000" },
];

const DEFAULT_ATTACHMENT_ROWS = [
  {
    name: "Bank statement - January 2026.pdf",
    represents: "Evidence of the organisation's bank account",
  },
  {
    name: "2025 financial statements.pdf",
    represents: "The organisation's most recent financial statements",
  },
];

const GUIDANCE_DOCUMENTS = [
  {
    kind: "Selection Criteria (GOG)",
    name: "NAIDOC 2026 Local Grants Opportunity - Grant Opportunity Guidelines.pdf",
    key: "gog",
  },
  {
    kind: "Application Form",
    name: "NAIDOC 2026 - Sample Application Form.pdf",
    key: "application_form",
  },
  {
    kind: "Applicants Guide",
    name: "NAIDOC 2026 Local Grants - Applicants Guide.pdf",
    key: "applicants_guide",
  },
];

const DEFAULT_APPLICANT_DRAFT = {
  legalName: "River Plains Community Association Inc",
  tradingName: "River Plains Community Association",
  abn: "00 000 000 000",
  entityType: "Incorporated association",
  organisationDescription:
    "A fictional First Nations-controlled community association that delivers cultural and family activities in regional NSW.",
  fundingStream: "stream_two",
  projectTitle: "Dubbo Family Cultural Arts and Storytelling Day",
  activityDescription:
    "River Plains Community Association will hold a free family cultural arts and storytelling day in Dubbo on 22 August 2026. First Nations cultural facilitators and artists will lead storytelling, weaving and visual-art workshops. The community-designed event will strengthen cultural expression, enable intergenerational participation and promote respectful understanding of First Nations histories, cultures and achievements.",
  startDate: "2026-08-22",
  endDate: "2026-08-22",
  coContributions:
    "Volunteer time, donated venue support and donated participant materials.",
  expectedAttendance: "260",
  attendanceFree: "yes",
  attendanceCost: "0",
  criterion1: "",
};

function ApplicantFieldFeedback({ section }) {
  if (!section) return <p className="awaiting">Not checked yet</p>;
  if (section.error) {
    return <div className="error-box compact-error">{section.error}</div>;
  }
  if (!section.findings.length) {
    return (
      <p className="clear-message">
        No issue identified by this isolated check.
      </p>
    );
  }
  return (
    <div className="field-findings">
      {section.findings.map((finding, index) => (
        <Finding finding={finding} key={index} />
      ))}
    </div>
  );
}

function matchBudgetFeedback(rows, items) {
  const normalise = (value) =>
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  const sentRowIndexes = rows
    .map((row, index) => (row.item.trim() && row.amount.trim() ? index : -1))
    .filter((index) => index !== -1);
  const feedback = new Map();
  const unmatched = [...items];

  sentRowIndexes.forEach((rowIndex) => {
    const rowName = normalise(rows[rowIndex].item);
    if (!rowName) return;
    const exact = unmatched.findIndex(
      (item) => normalise(item.item) === rowName,
    );
    const found =
      exact !== -1
        ? exact
        : unmatched.findIndex((item) => {
            const itemName = normalise(item.item);
            return itemName.includes(rowName) || rowName.includes(itemName);
          });
    if (found !== -1) {
      feedback.set(rowIndex, unmatched[found]);
      unmatched.splice(found, 1);
    }
  });

  if (items.length === sentRowIndexes.length) {
    sentRowIndexes.forEach((rowIndex, position) => {
      if (!feedback.has(rowIndex) && unmatched.includes(items[position])) {
        feedback.set(rowIndex, items[position]);
      }
    });
  }
  return feedback;
}

export default function ApplicantView() {
  const [draft, setDraft] = useState(DEFAULT_APPLICANT_DRAFT);
  const [rows, setRows] = useState(DEFAULT_ROWS);
  const [attachmentRows, setAttachmentRows] = useState(
    DEFAULT_ATTACHMENT_ROWS,
  );
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({
    phase: "reviewing",
    sections: [],
    current: 0,
  });
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(null);
  const checkInFlight = useRef(false);
  const sections = useMemo(
    () =>
      new Map((result?.sections || []).map((section) => [section.id, section])),
    [result],
  );
  const budgetFeedback = useMemo(
    () => matchBudgetFeedback(rows, sections.get("budget")?.budget_items || []),
    [rows, sections],
  );
  const budgetTotal = useMemo(
    () =>
      rows.reduce(
        (total, row) => total + (Number(row.amount.replaceAll(",", "")) || 0),
        0,
      ),
    [rows],
  );

  function mutateApplicantInput(mutation) {
    if (checkInFlight.current) return;
    mutation();
    setResult(null);
    setError("");
  }

  function updateDraft(key, value) {
    mutateApplicantInput(() =>
      setDraft((current) => ({ ...current, [key]: value })),
    );
  }

  function updateRow(index, key, value) {
    mutateApplicantInput(() =>
      setRows((current) =>
        current.map((row, rowIndex) =>
          rowIndex === index ? { ...row, [key]: value } : row,
        ),
      ),
    );
  }

  function removeRow(index) {
    mutateApplicantInput(() =>
      setRows((current) => current.filter((_, rowIndex) => rowIndex !== index)),
    );
  }

  function addRow() {
    mutateApplicantInput(() =>
      setRows((current) => [...current, { item: "", amount: "" }]),
    );
  }

  function updateAttachmentRow(index, key, value) {
    mutateApplicantInput(() =>
      setAttachmentRows((current) =>
        current.map((row, rowIndex) =>
          rowIndex === index ? { ...row, [key]: value } : row,
        ),
      ),
    );
  }

  function removeAttachmentRow(index) {
    mutateApplicantInput(() =>
      setAttachmentRows((current) =>
        current.filter((_, rowIndex) => rowIndex !== index),
      ),
    );
  }

  function addAttachmentRow() {
    mutateApplicantInput(() =>
      setAttachmentRows((current) => [
        ...current,
        { name: "", represents: "" },
      ]),
    );
  }

  async function submit(event) {
    event.preventDefault();
    if (checkInFlight.current) return;
    checkInFlight.current = true;
    setLoading(true);
    setError("");
    setResult(null);
    setProgress({ phase: "reviewing", sections: [], current: 0 });

    try {
      if (!draft.legalName.trim() || !draft.projectTitle.trim()) {
        throw new Error(
          "Complete the applicant name and activity title before checking the draft.",
        );
      }
      if (!draft.activityDescription.trim()) {
        throw new Error(
          "Add an activity description before checking the draft.",
        );
      }
      if (draft.fundingStream === "stream_three" && !draft.criterion1.trim()) {
        throw new Error(
          "Complete the Stream Three assessment criterion before checking the draft.",
        );
      }

      const activeRows = rows.filter(
        (row) => row.item.trim() && row.amount.trim(),
      );
      if (activeRows.length < 2) {
        throw new Error(
          "Add at least two budget lines before checking the draft.",
        );
      }
      const listedAttachments = attachmentRows.filter(
        (row) => row.name.trim() || row.represents.trim(),
      );
      if (
        listedAttachments.some(
          (row) => !row.name.trim() || !row.represents.trim(),
        )
      ) {
        throw new Error(
          "Complete both fields for each listed attachment before checking the draft.",
        );
      }

      const fields = [
        {
          id: "activity_description",
          header: "Activity description and alignment",
          type: "description",
          text: draft.activityDescription.trim(),
          order: 1,
        },
      ];
      let nextOrder = 2;
      if (draft.fundingStream === "stream_three" && draft.criterion1.trim()) {
        fields.push({
          id: "criterion_1",
          header: "Criterion 1: experience, resources and capability",
          type: "criterion",
          text: draft.criterion1.trim(),
          order: nextOrder,
        });
        nextOrder += 1;
      }
      fields.push({
        id: "budget",
        header: "Budget",
        type: "budget",
        text: activeRows
          .map((row) => `${row.item.trim()} | $${row.amount.trim()}`)
          .join("\n"),
        order: nextOrder,
      });
      nextOrder += 1;
      fields.push({
        id: "attachments",
        header: "Attachment checklist",
        type: "attachments",
        text: listedAttachments.length
          ? listedAttachments
              .map(
                (row, index) =>
                  `${index + 1}. ${row.name.trim()} | Represents: ${row.represents.trim()}`,
              )
              .join("\n")
          : "No attachments listed.",
        order: nextOrder,
      });
      setProgress({
        phase: "reviewing",
        sections: fields.map(({ id, header }) => ({ id, header })),
        current: 1,
      });

      const data = new FormData();
      data.append("gog", await fetchDemoFile("gog"));
      data.append("application_form", await fetchDemoFile("application_form"));
      data.append(
        "supporting_documents",
        await fetchDemoFile("applicants_guide"),
      );
      data.append("fields", JSON.stringify(fields));
      setResult(
        await checkApplicant(data, (update) => {
          if (update.type === "fields") {
            setProgress({
              phase: "reviewing",
              sections: update.fields || [],
              current: update.fields?.length ? 1 : 0,
            });
          } else if (
            update.type === "progress" &&
            update.phase === "reviewing"
          ) {
            setProgress((current) => ({
              ...current,
              phase: "reviewing",
              current: update.current,
            }));
          } else if (update.type === "complete") {
            setProgress((current) => ({
              ...current,
              phase: "complete",
              current: current.sections.length + 1,
            }));
          }
        }),
      );
    } catch (caught) {
      setError(caught.message || "The check could not be completed.");
    } finally {
      checkInFlight.current = false;
      setLoading(false);
    }
  }

  return (
    <div className="applicant-layout">
      <section>
        <div className="section-intro">
          <span className="eyebrow">Applicant view</span>
          <h2>Build and check your application draft</h2>
          <p>
            This synthetic form mirrors the main parts of the 2026 NAIDOC
            application. GOGgles checks marked answers against the supplied
            guidance while you remain the author.
          </p>
        </div>
        <section
          className="applicant-guidance"
          aria-labelledby="applicant-guidance-title"
        >
          <div className="applicant-guidance-heading">
            <div>
              <h3 id="applicant-guidance-title">
                Guidance used for these checks
              </h3>
              <p>Read-only NAIDOC source documents</p>
            </div>
            <span>Preloaded</span>
          </div>
          <div className="applicant-guidance-documents">
            {GUIDANCE_DOCUMENTS.map((document) => (
              <article
                className="applicant-guidance-document"
                key={document.key}
              >
                <span className="guidance-pdf-mark" aria-hidden="true">
                  PDF
                </span>
                <div>
                  <span>{document.kind}</span>
                  <strong title={document.name}>{document.name}</strong>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setPreview({
                      label: document.name,
                      url: `/api/demo/files/${document.key}`,
                    })
                  }
                  aria-label={`Preview ${document.kind}`}
                >
                  Preview
                </button>
              </article>
            ))}
          </div>
        </section>
        <div className="demo-data-note">
          <strong>Prototype data only</strong>
          <span>
            Use fictional or authorised information. Administrative details stay
            in your browser; only fields marked “AI check” are sent to GOGgles for
            review.
          </span>
        </div>
        <form onSubmit={submit} className="applicant-form">
          <fieldset className="applicant-inputs" disabled={loading}>
            <section className="applicant-section">
              <div className="applicant-section-heading">
                <span>1</span>
                <div>
                  <h3>Applicant details</h3>
                  <p>Tell us about the organisation applying for the grant.</p>
                </div>
              </div>
              <div className="form-grid">
                <label className="field field-wide">
                  <span>Applicant legal name *</span>
                  <input
                    value={draft.legalName}
                    onChange={(event) =>
                      updateDraft("legalName", event.target.value)
                    }
                  />
                </label>
                <label className="field">
                  <span>Registered business name</span>
                  <input
                    value={draft.tradingName}
                    onChange={(event) =>
                      updateDraft("tradingName", event.target.value)
                    }
                  />
                </label>
                <label className="field">
                  <span>ABN</span>
                  <input
                    value={draft.abn}
                    onChange={(event) => updateDraft("abn", event.target.value)}
                  />
                </label>
                <label className="field">
                  <span>Legal entity type *</span>
                  <select
                    value={draft.entityType}
                    onChange={(event) =>
                      updateDraft("entityType", event.target.value)
                    }
                  >
                    <option>Incorporated association</option>
                    <option>Indigenous corporation</option>
                    <option>Company</option>
                    <option>Local government</option>
                    <option>Educational institution</option>
                    <option>Sole trader</option>
                    <option>Partnership</option>
                  </select>
                </label>
                <label className="field field-full">
                  <span>Organisation description</span>
                  <textarea
                    rows={4}
                    value={draft.organisationDescription}
                    onChange={(event) =>
                      updateDraft("organisationDescription", event.target.value)
                    }
                  />
                  <small>
                    Prototype context field requested for this demo. It stays
                    local and is not used to resolve another answer.
                  </small>
                </label>
              </div>
            </section>

            <section className="applicant-section">
              <div className="applicant-section-heading">
                <span>2</span>
                <div>
                  <h3>Activity or event</h3>
                  <p>
                    Describe what you propose to deliver and where it will
                    happen.
                  </p>
                </div>
              </div>
              <div className="form-grid">
                <label className="field">
                  <span>Funding stream *</span>
                  <select
                    value={draft.fundingStream}
                    onChange={(event) =>
                      updateDraft("fundingStream", event.target.value)
                    }
                  >
                    <option value="stream_one">
                      Stream One: Educational institutions (up to $1,500)
                    </option>
                    <option value="stream_two">
                      Stream Two: Small-scale (up to $10,000)
                    </option>
                    <option value="stream_three">
                      Stream Three: Large-scale ($10,000–$25,000)
                    </option>
                  </select>
                </label>
                <label className="field">
                  <span>Short activity title *</span>
                  <input
                    value={draft.projectTitle}
                    onChange={(event) =>
                      updateDraft("projectTitle", event.target.value)
                    }
                    maxLength={250}
                  />
                </label>
                <label className="field field-full ai-field">
                  <span className="field-label-row">
                    <span>Activity description and alignment *</span>
                    <span className="ai-check-label">AI check</span>
                  </span>
                  <textarea
                    rows={7}
                    value={draft.activityDescription}
                    onChange={(event) =>
                      updateDraft("activityDescription", event.target.value)
                    }
                    maxLength={2000}
                  />
                  <small>
                    {draft.activityDescription.length}/2,000 characters ·
                    Explain the activity and how it meets the grant objectives.
                  </small>
                  <ApplicantFieldFeedback
                    section={sections.get("activity_description")}
                  />
                </label>
                <label className="field">
                  <span>Proposal start date *</span>
                  <input
                    type="date"
                    value={draft.startDate}
                    onChange={(event) =>
                      updateDraft("startDate", event.target.value)
                    }
                  />
                </label>
                <label className="field">
                  <span>Proposal end date *</span>
                  <input
                    type="date"
                    value={draft.endDate}
                    onChange={(event) =>
                      updateDraft("endDate", event.target.value)
                    }
                  />
                </label>
                <label className="field field-full">
                  <span>Co-contributions</span>
                  <textarea
                    rows={3}
                    value={draft.coContributions}
                    onChange={(event) =>
                      updateDraft("coContributions", event.target.value)
                    }
                    maxLength={250}
                  />
                  <small>
                    {draft.coContributions.length}/250 characters · Include
                    financial and non-financial contributions.
                  </small>
                </label>
                <label className="field">
                  <span>Expected attendance *</span>
                  <input
                    type="number"
                    min="0"
                    value={draft.expectedAttendance}
                    onChange={(event) =>
                      updateDraft("expectedAttendance", event.target.value)
                    }
                  />
                </label>
                <label className="field">
                  <span>Is attendance free? *</span>
                  <select
                    value={draft.attendanceFree}
                    onChange={(event) =>
                      updateDraft("attendanceFree", event.target.value)
                    }
                  >
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                </label>
                {draft.attendanceFree === "no" && (
                  <label className="field">
                    <span>Cost per person</span>
                    <input
                      inputMode="decimal"
                      value={draft.attendanceCost}
                      onChange={(event) =>
                        updateDraft("attendanceCost", event.target.value)
                      }
                    />
                  </label>
                )}
              </div>
            </section>

            {draft.fundingStream === "stream_three" && (
              <section className="applicant-section conditional-section">
                <div className="applicant-section-heading">
                  <span>3</span>
                  <div>
                    <h3>Stream Three assessment criterion</h3>
                    <p>This question appears for requests above $10,000.</p>
                  </div>
                </div>
                <label className="field ai-field">
                  <span className="field-label-row">
                    <span>Experience, resources and capability *</span>
                    <span className="ai-check-label">AI check</span>
                  </span>
                  <textarea
                    rows={10}
                    value={draft.criterion1}
                    onChange={(event) =>
                      updateDraft("criterion1", event.target.value)
                    }
                    maxLength={6000}
                  />
                  <small>
                    {draft.criterion1.length}/6,000 characters · Address value,
                    experience, resources, risks and intended outcomes.
                  </small>
                  <ApplicantFieldFeedback section={sections.get("criterion_1")} />
                </label>
              </section>
            )}

            <section className="applicant-section">
              <div className="applicant-section-heading">
                <span>
                  {draft.fundingStream === "stream_three" ? "4" : "3"}
                </span>
                <div>
                  <h3>Funding request and budget</h3>
                  <p>Itemise the grant funding requested, excluding GST.</p>
                </div>
              </div>
              <div className="budget-panel ai-field">
                <div className="budget-editor">
                  <div className="budget-row budget-head">
                    <span>Budget item</span>
                    <span>Amount (GST excl.)</span>
                    <span>AI check guidance</span>
                  </div>
                  {rows.map((row, index) => {
                    const itemFeedback = budgetFeedback.get(index);
                    return (
                      <div className="budget-row" key={index}>
                        <div className="budget-item-input">
                          <label
                            className="budget-cell-label"
                            htmlFor={`budget-item-${index + 1}`}
                          >
                            Budget item {index + 1}
                          </label>
                          <input
                            id={`budget-item-${index + 1}`}
                            aria-label={`Budget item ${index + 1}`}
                            value={row.item}
                            onChange={(event) =>
                              updateRow(index, "item", event.target.value)
                            }
                          />
                          <button
                            type="button"
                            className="remove-line-button"
                            disabled={rows.length <= 2}
                            onClick={() => removeRow(index)}
                            aria-label={`Remove budget line ${index + 1}`}
                          >
                            Remove
                          </button>
                        </div>
                        <div className="money-input">
                          <label
                            className="budget-cell-label"
                            htmlFor={`budget-amount-${index + 1}`}
                          >
                            Amount (GST excl.)
                          </label>
                          <span>$</span>
                          <input
                            id={`budget-amount-${index + 1}`}
                            aria-label={`Amount ${index + 1}`}
                            inputMode="decimal"
                            value={row.amount}
                            onChange={(event) =>
                              updateRow(index, "amount", event.target.value)
                            }
                          />
                        </div>
                        <div className="inline-feedback">
                          <span className="budget-cell-label budget-feedback-label">
                            AI check guidance
                          </span>
                          {itemFeedback ? (
                            <>
                              <ClassificationBadge
                                value={itemFeedback.classification}
                              />
                              {itemFeedback.comment && (
                                <p>{itemFeedback.comment}</p>
                              )}
                              {itemFeedback.suggested_action && (
                                <p className="action">
                                  {itemFeedback.suggested_action}
                                </p>
                              )}
                              <ClarificationEvidence
                                evidence={itemFeedback.clarification_evidence}
                              />
                              <SourceList sources={itemFeedback.sources} />
                            </>
                          ) : (
                            <span className="awaiting">Not checked yet</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="budget-footer">
                <button type="button" className="text-button" onClick={addRow}>
                  + Add budget line
                </button>
                <div className="budget-total">
                  <span>Total funding requested</span>
                  <strong>
                    $
                    {budgetTotal.toLocaleString("en-AU", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </strong>
                </div>
              </div>
            </section>

            <section className="applicant-section">
              <div className="applicant-section-heading">
                <span>
                  {draft.fundingStream === "stream_three" ? "5" : "4"}
                </span>
                <div>
                  <h3>Attachments</h3>
                  <p>
                    List the documents you intend to include and what each one
                    represents.
                  </p>
                </div>
              </div>
              <div className="attachment-checklist ai-field">
                <div className="field-label-row attachment-checklist-title">
                  <strong>Attachment checklist</strong>
                  <span className="ai-check-label">AI check</span>
                </div>
                <div className="attachment-rows">
                  {attachmentRows.length ? (
                    attachmentRows.map((row, index) => (
                      <div className="attachment-row" key={index}>
                        <div className="attachment-row-heading">
                          <strong>Attachment {index + 1}</strong>
                          <button
                            type="button"
                            className="remove-line-button"
                            onClick={() => removeAttachmentRow(index)}
                            aria-label={`Remove attachment ${index + 1}`}
                          >
                            Remove
                          </button>
                        </div>
                        <div className="attachment-fields">
                          <label className="field">
                            <span>Attachment name</span>
                            <input
                              value={row.name}
                              placeholder="For example, bank statement.pdf"
                              onChange={(event) =>
                                updateAttachmentRow(
                                  index,
                                  "name",
                                  event.target.value,
                                )
                              }
                            />
                          </label>
                          <label className="field">
                            <span>What this attachment represents</span>
                            <input
                              value={row.represents}
                              placeholder="For example, bank account evidence"
                              onChange={(event) =>
                                updateAttachmentRow(
                                  index,
                                  "represents",
                                  event.target.value,
                                )
                              }
                            />
                          </label>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="attachment-empty">No attachments listed.</p>
                  )}
                </div>
                <button
                  type="button"
                  className="text-button attachment-add-button"
                  onClick={addAttachmentRow}
                >
                  + Add attachment
                </button>
                <ApplicantFieldFeedback section={sections.get("attachments")} />
              </div>
            </section>
          </fieldset>

          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}
          <p className="advisory-copy">
            <strong>Review assistance only.</strong>{" "}
            GOGgles never auto-rejects or stops an application from proceeding.
            Applicants verify every finding, decide whether to act and remain the
            author of every change.
          </p>
          <div className="submit-row">
            <p>Each marked answer is checked in a separate call.</p>
            <button className="primary-button" disabled={loading}>
              {loading ? "Checking draft…" : "Check assessable fields"}
            </button>
          </div>
          {loading && (
            <AssessmentProgress
              progress={progress}
              includeExtraction={false}
              itemLabel="fields"
              preparingLabel="Preparing field reviews"
              message="This can take a few minutes. Keep this page open while GOGgles checks each marked field separately."
            />
          )}
        </form>
      </section>
      <PreviewModal preview={preview} onClose={() => setPreview(null)} />
    </div>
  );
}
