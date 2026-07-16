import { useEffect, useRef, useState } from "react";

import { checkAssessor, fetchDemoFile } from "../api";
import AssessmentProgress from "../components/AssessmentProgress";
import {
  DropZone,
  FileChip,
  PreviewModal,
  RequirementBadge,
  UploadCard,
} from "../components/Documents";
import { ResultPanel } from "../components/Feedback";

const DEMO_APPLICATIONS = [
  ["application_01", "Synthetic Grant Proposal 1 (Out-of-scope budget items)"],
  ["application_02", "Synthetic Grant Proposal 2 (Vague budget lines)"],
  ["application_03", "Synthetic Grant Proposal 3 (Funding stream review)"],
  ["application_04", "Synthetic Grant Proposal 4 (Weak Stream Three criterion)"],
  ["application_05", "Synthetic Grant Proposal 5 (Missing bank evidence)"],
  ["application_06", "Synthetic Grant Proposal 6 (Clean control)"],
];

async function sourceFile(upload, useDefault, demoKey) {
  if (upload) return upload;
  if (useDefault) return fetchDemoFile(demoKey);
  throw new Error("Add each required source document before running the check.");
}

function ExampleResultsShortcut({ status }) {
  const copy = {
    running: {
      title: "See completed examples while you wait.",
      body: "Open six captured synthetic checks in a new tab. This live run will continue here.",
    },
    complete: {
      title: "Compare this run with the examples.",
      body: "Open the six captured checks alongside the result GOGgles just returned.",
    },
    available: {
      title: "See a completed check instead.",
      body: "The Example results page has six captured synthetic checks ready to review.",
    },
  }[status];

  return (
    <aside className={`example-results-shortcut is-${status}`}>
      <div>
        <strong>{copy.title}</strong>
        <p>{copy.body}</p>
      </div>
      <a
        href="/example-results"
        target="_blank"
        rel="noreferrer"
        aria-label="Open example results in a new tab"
      >
        Open example results <span aria-hidden="true">↗</span>
      </a>
    </aside>
  );
}

export default function AssessorView() {
  const [gog, setGog] = useState(null);
  const [applicationForm, setApplicationForm] = useState(null);
  const [supportingFiles, setSupportingFiles] = useState([]);
  const [useDefaultGog, setUseDefaultGog] = useState(true);
  const [useDefaultForm, setUseDefaultForm] = useState(true);
  const [useDefaultSupport, setUseDefaultSupport] = useState(true);
  const [application, setApplication] = useState(null);
  const [useDemoApplication, setUseDemoApplication] = useState(true);
  const [demoKey, setDemoKey] = useState("application_01");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({
    phase: "extracting",
    sections: [],
    current: 0,
  });
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(null);
  const [hasStartedCheck, setHasStartedCheck] = useState(false);
  const checkInFlight = useRef(false);

  useEffect(
    () => () => {
      if (preview?.objectUrl) URL.revokeObjectURL(preview.url);
    },
    [preview],
  );

  function openPreview(file, demoFileKey, label) {
    setPreview({
      label,
      url: file ? URL.createObjectURL(file) : `/api/demo/files/${demoFileKey}`,
      objectUrl: Boolean(file),
    });
  }

  function mutateAssessmentInput(mutation) {
    if (checkInFlight.current) return;
    mutation();
    setResult(null);
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    if (checkInFlight.current) return;
    checkInFlight.current = true;
    setHasStartedCheck(true);
    setLoading(true);
    setError("");
    setResult(null);
    setProgress({ phase: "extracting", sections: [], current: 0 });

    try {
      const data = new FormData();
      data.append("gog", await sourceFile(gog, useDefaultGog, "gog"));
      data.append(
        "application_form",
        await sourceFile(
          applicationForm,
          useDefaultForm,
          "application_form",
        ),
      );

      const supportFiles = [...supportingFiles];
      if (useDefaultSupport) {
        supportFiles.unshift(await fetchDemoFile("applicants_guide"));
      }
      supportFiles.forEach((item) =>
        data.append("supporting_documents", item),
      );
      data.append(
        "grant_application",
        await sourceFile(application, useDemoApplication, demoKey),
      );

      const response = await checkAssessor(data, (update) => {
        if (update.type === "progress" && update.phase === "extracting") {
          setProgress({ phase: "extracting", sections: [], current: 0 });
        } else if (update.type === "sections") {
          setProgress({
            phase: "reviewing",
            sections: update.sections || [],
            current: 0,
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
      });
      setResult(response);
    } catch (caught) {
      setError(caught.message || "The check could not be completed.");
    } finally {
      checkInFlight.current = false;
      setLoading(false);
    }
  }

  const selectedDemoLabel =
    DEMO_APPLICATIONS.find(([key]) => key === demoKey)?.[1] ||
    "Synthetic Grant Proposal";

  return (
    <div className="view-layout">
      <section>
        <div className="section-intro">
          <span className="eyebrow">Assessor view</span>
          <h2>Review a submitted grant proposal</h2>
          <p>
            Attach the grant proposal, rulebook and application form. Supporting
            documents are optional. GOGgles checks the implemented mechanical
            issues and keeps every judgement with you.
          </p>
        </div>
        <div className="demo-data-note">
          <strong>Prototype sources</strong>
          <span>
            The default NAIDOC 2026 grant opportunity documents were sourced
            publicly from grants.gov.au. All synthetic grant proposals are
            entirely fictional and contain no real applicant information.
          </span>
        </div>
        <form onSubmit={submit} className="check-form">
          <p className="program-scope-note">
            For IM2026, NAIDOC 2026 is the tested default; the GOGgles workflow
            is designed to adapt to other grant programs, but they have not been
            tested in this prototype.
          </p>
          <div className="upload-grid">
            <div className="upload-card application-card">
              <div
                className={`upload-number ${
                  application || useDemoApplication
                    ? "has-document"
                    : "no-document"
                }`}
                aria-hidden="true"
              >
                {application || useDemoApplication ? "✓" : "1"}
              </div>
              <div className="upload-copy">
                <div className="upload-title-row">
                  <h3>Grant Proposal</h3>
                  <RequirementBadge required />
                </div>
                <p>
                  Preview the attached synthetic proposal, or clear it to upload
                  another test PDF.
                </p>
                {useDemoApplication && !application && (
                  <div className="proposal-default">
                    <select
                      aria-label="Attached synthetic grant proposal"
                      value={demoKey}
                      disabled={loading}
                      onChange={(event) =>
                        mutateAssessmentInput(() =>
                          setDemoKey(event.target.value),
                        )
                      }
                    >
                      {DEMO_APPLICATIONS.map(([key, label]) => (
                        <option value={key} key={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                    <span className="proposal-actions">
                      <button
                        type="button"
                        className="preview-file"
                        onClick={() =>
                          openPreview(null, demoKey, selectedDemoLabel)
                        }
                      >
                        Preview
                      </button>
                      <button
                        type="button"
                        disabled={loading}
                        onClick={() =>
                          mutateAssessmentInput(() =>
                            setUseDemoApplication(false),
                          )
                        }
                      >
                        Clear
                      </button>
                    </span>
                  </div>
                )}
                {application && (
                  <FileChip
                    label={application.name}
                    onPreview={() =>
                      openPreview(application, null, application.name)
                    }
                    onClear={() =>
                      mutateAssessmentInput(() => setApplication(null))
                    }
                    clearDisabled={loading}
                  />
                )}
                {!application && !useDemoApplication && (
                  <>
                    <DropZone
                      onFiles={(files) => {
                        mutateAssessmentInput(() => {
                          setApplication(files[0]);
                          setUseDemoApplication(false);
                        });
                      }}
                      label="Drop grant proposal PDF here or browse"
                      disabled={loading}
                    />
                    <button
                      type="button"
                      className="text-button restore-default"
                      disabled={loading}
                      onClick={() =>
                        mutateAssessmentInput(() =>
                          setUseDemoApplication(true),
                        )
                      }
                    >
                      Restore selected synthetic proposal
                    </button>
                  </>
                )}
              </div>
            </div>
            <UploadCard
              step="2"
              required
              title="Selection Criteria (GOG)"
              detail="The primary source for every rule."
              defaultLabel="NAIDOC 2026 Local Grants Opportunity - Grant Opportunity Guidelines.pdf"
              defaultKey="gog"
              useDefault={useDefaultGog}
              setUseDefault={(value) =>
                mutateAssessmentInput(() => setUseDefaultGog(value))
              }
              file={gog}
              setFile={(value) =>
                mutateAssessmentInput(() => setGog(value))
              }
              onPreview={openPreview}
              mutationDisabled={loading}
            />
            <UploadCard
              step="3"
              required
              title="Application Form"
              detail="Field instructions and required responses."
              defaultLabel="NAIDOC 2026 - Sample Application Form.pdf"
              defaultKey="application_form"
              useDefault={useDefaultForm}
              setUseDefault={(value) =>
                mutateAssessmentInput(() => setUseDefaultForm(value))
              }
              file={applicationForm}
              setFile={(value) =>
                mutateAssessmentInput(() => setApplicationForm(value))
              }
              onPreview={openPreview}
              mutationDisabled={loading}
            />
            <UploadCard
              step="4"
              title="Supporting Documents"
              detail="Optional applicant guides and additional context."
              defaultLabel="NAIDOC 2026 Local Grants - Applicants Guide.pdf"
              defaultKey="applicants_guide"
              useDefault={useDefaultSupport}
              setUseDefault={(value) =>
                mutateAssessmentInput(() => setUseDefaultSupport(value))
              }
              file={supportingFiles}
              setFile={(value) =>
                mutateAssessmentInput(() => setSupportingFiles(value))
              }
              onPreview={openPreview}
              multiple
              mutationDisabled={loading}
            />
          </div>
          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}
          <aside className="advisory-note" aria-label="Advisory review safeguard">
            <strong>Review assistance only</strong>
            <span>
              GOGgles never auto-rejects or stops an application from proceeding.
              Assessors verify every finding and retain responsibility for any
              follow-up and assessment decision.
            </span>
          </aside>
          <div className="submit-row">
            <p>
              Use only public, synthetic or authorised test PDFs. Files are sent
              to Gemini for this check and are not saved by GOGgles.
            </p>
            <button className="primary-button" disabled={loading}>
              {loading ? "Checking grant proposal…" : "Check grant proposal"}
            </button>
          </div>
          {hasStartedCheck && (
            <ExampleResultsShortcut
              status={result ? "complete" : loading ? "running" : "available"}
            />
          )}
          {loading && <AssessmentProgress progress={progress} />}
        </form>
      </section>
      {result && <ResultPanel result={result} />}
      <PreviewModal preview={preview} onClose={() => setPreview(null)} />
    </div>
  );
}
