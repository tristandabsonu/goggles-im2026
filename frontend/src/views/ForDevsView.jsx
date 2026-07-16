const GEMINI_FLASH_URL =
  "https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash";
const GEMINI_PDF_URL =
  "https://ai.google.dev/gemini-api/docs/document-processing";

export default function ForDevsView() {
  return (
    <main id="main-content" className="how-page dev-page" tabIndex={-1}>
      <section className="examples-hero">
        <div className="examples-hero-inner">
          <span className="eyebrow">For the devs</span>
          <h1>The technical choices behind GOGgles.</h1>
          <p>
            A small, stateless prototype built to make one document-heavy
            workflow easy to test, inspect and explain.
          </p>
        </div>
      </section>

      <div className="how-inner">
        <section className="how-narrative" aria-label="GOGgles design choices">
          <article className="how-narrative-row">
            <h2>Model choice</h2>
            <div className="how-narrative-copy">
              <p>
                Gemini was the practical fit because it accepts PDFs directly,
                supports schema-constrained structured output and gives the Flash
                models used here a one-million-token input window. The complete
                labelled document bundle can stay together in one request instead
                of going through an OCR, chunking or retrieval pipeline.
              </p>
              <p className="how-scale">
                <strong>123 pages</strong>
                <span>
                  About 3.1 MB in the largest preloaded Assessor bundle, before the
                  prompt. That is comfortably inside Gemini&apos;s PDF and context
                  limits.
                </span>
              </p>
              <p>
                The captured examples were produced with Gemini 3.5 Flash. Live
                checks are configurable, and development also used Gemini 3 Flash
                Preview. Flash kept the sequential, multi-call workflow responsive
                enough for the demo and performed satisfactorily on the defined
                synthetic cases.
              </p>
              <p>
                For a production pipeline, a Pro-class model would also be worth
                evaluating for slower review work where response time matters less.
                Any quality gain would need to be measured against cost, missed
                issues and false positives rather than assumed from model size.
              </p>
              <p>
                Claude models were also trialled during development. Some outputs
                were stronger, but the improvement did not justify the extra cost
                for this prototype. That was an informal project trade-off, not a
                general model benchmark.
              </p>
              <p className="how-sources">
                References: <a href={GEMINI_FLASH_URL}>Gemini 3.5 Flash</a>
                {" · "}
                <a href={GEMINI_PDF_URL}>Gemini PDF processing</a>
              </p>
            </div>
          </article>

          <article className="how-narrative-row">
            <h2>Request shape</h2>
            <div className="how-narrative-copy">
              <p>
                Assessor mode uses two passes. The first reads only the Application
                Form and proposal to identify stable section IDs. The second checks
                up to four supported sections against the complete labelled bundle,
                one call at a time. Sequential calls keep a section failure from
                hiding the other results and let the interface show real progress.
              </p>
              <p>
                Writer mode skips extraction because the interface already knows
                its fields. Each draft field being checked is sent separately with
                only the applicant-facing guidance documents. Other draft answers
                are excluded by request construction, so one field cannot silently
                fill a gap in another.
              </p>
            </div>
          </article>

          <article className="how-narrative-row">
            <h2>Stateless by design</h2>
            <div className="how-narrative-copy">
              <p>
                FastAPI validates each PDF, holds its bytes in memory for the
                request and sends it to Gemini as a native PDF part. GOGgles does
                not write uploads to disk or a database. The React build and API are
                served by the same small service, with no accounts, separate worker
                service or persistent job queue.
              </p>
              <p>
                That keeps the prototype simple and makes its data path easy to
                explain. When a request ends, GOGgles retains no upload or result
                history. That is not a production privacy claim: provider handling,
                retention, consent, security and data sovereignty would still need
                formal decisions before real applications were used.
              </p>
            </div>
          </article>

          <article className="how-narrative-row">
            <h2>Small on purpose</h2>
            <div className="how-narrative-copy">
              <p>
                There is no vector database, agent framework, multi-provider layer
                or general citation-verification system. Structured response models
                keep the output shape predictable, targeted local checks guard the
                demonstrated edge cases, and every finding remains something a
                person must verify.
              </p>
              <p>
                The prototype is intentionally limited to the named NAIDOC checks
                and synthetic scenarios. A production path would start with broader
                grant-program evaluation, integration and governance. A larger model
                would not replace evidence about false positives, missed issues,
                cost and real user outcomes.
              </p>
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}
