import WorkflowSequence from "../components/WorkflowSequence";

const ANNUAL_REPORT_URL =
  "https://www.niaa.gov.au/news-and-media/niaa-annual-report-2024-25";
const APPLICATION_SURVEY_URL =
  "https://www.niaa.gov.au/sites/default/files/documents/2026-02/RJED-R1-and-2-Feedback-Survey-Results.pdf";

export default function HowItWorksView() {
  return (
    <main id="main-content" className="how-page" tabIndex={-1}>
      <section className="examples-hero">
        <div className="examples-hero-inner">
          <span className="eyebrow">How it works</span>
          <h1>Put judgement back at the centre of grant assessment.</h1>
          <p>
            The mechanical part of a grant check is the part a machine can do.
            GOGgles takes that first pass and shows its sources, so people can
            spend their time on merit, evidence and local context.
          </p>
        </div>
      </section>

      <div className="how-inner">
        <section className="how-narrative" aria-label="Why GOGgles">
          <article className="how-narrative-row">
            <h2>The problem</h2>
            <div className="how-narrative-copy">
              <p>
                Grant applications are assessed against Grant Opportunity
                Guidelines: dense documents of eligibility rules, assessment
                criteria, required attachments and out-of-scope lists. Applicants
                without grant-writing experience can submit otherwise worthwhile
                proposals with avoidable gaps. Assessors then spend time finding
                vague budget items, missing attachments and basic rule mismatches
                instead of applying judgement and context.
              </p>
              <p className="how-scale">
                <strong>$1.806 billion</strong>
                <span>
                  in grant expenses recorded by NIAA in 2024–25. At that scale,
                  even small points of friction repeat.
                </span>
              </p>
              <p>
                This is not a hypothetical problem. NIAA&apos;s 2026 survey of Remote
                Jobs grant applicants received 54 responses. The complexity
                of the application process was one of four themes: respondents
                described the guidelines as complex and the financials and budget
                template as difficult to complete.
              </p>
              <p className="how-sources">
                Sources: <a href={ANNUAL_REPORT_URL}>NIAA Annual Report 2024–25</a>
                {" · "}
                <a href={APPLICATION_SURVEY_URL}>RJED applicant survey</a>
              </p>
            </div>
          </article>

          <article className="how-narrative-row">
            <h2>The vision</h2>
            <div className="how-narrative-copy">
              <p>
                A leveller for the grants process. Communities without
                grant-writing experience get the kind of feedback an experienced
                writer would give before submission, while assessors get the
                mechanical first pass done for them, freeing their judgement for
                merit, evidence and local context. Every finding traces back to the
                supplied guidance for a person to verify, and every decision
                remains with a human.
              </p>
            </div>
          </article>

          <article className="how-narrative-row">
            <h2>The idea</h2>
            <div className="how-narrative-copy">
              <p>
                One assessment engine, two views. The Writer view checks a draft
                before submission and shows the applicant what needs attention
                without writing the answer for them. The Assessor view checks a
                submitted application against its rulebook and surfaces the
                mechanical issues that would otherwise need to be found by hand.
              </p>
              <p>
                The result is simple: a comment, a suggested next step and the
                relevant source. A person verifies the evidence, writes any change
                and makes every assessment or funding decision.
              </p>
              <p className="how-principle">
                <strong>GOGgles is not a submission gatekeeper.</strong>{" "}
                A writer can still submit when a field is unchecked or flagged,
                and the application continues if the AI check fails. GOGgles
                never auto-rejects an application.
              </p>
            </div>
          </article>
        </section>

        <WorkflowSequence />

        <section className="how-risks" aria-labelledby="how-risks-title">
          <div className="how-section-intro">
            <h2 id="how-risks-title">Risks and limitations.</h2>
            <p>
              GOGgles is a useful first pass, not an authoritative assessment.
              Its findings should make human review more focused, never replace it.
            </p>
          </div>

          <div className="how-risk-list">
            <article className="how-risk-row">
              <h3>AI can be confidently wrong.</h3>
              <p>
                GOGgles may invent a finding, misread a rule, miss an important
                qualification or point to the wrong source. Every comment and
                citation needs to be checked against the supplied documents
                before anyone acts on it.
              </p>
            </article>

            <article className="how-risk-row">
              <h3>Cultural context requires people.</h3>
              <p>
                Documents alone cannot establish cultural authority, community
                support, local protocols or whether an activity is appropriate
                for a particular community. Those judgements belong with
                communities and experienced human assessors.
              </p>
            </article>

            <article className="how-risk-row">
              <h3>Sensitive applications need careful governance.</h3>
              <p>
                Grant applications can contain personal, financial, commercial
                or culturally sensitive information. This prototype does not
                save uploads, but checked content is sent to an external AI
                provider. Any real-world use would need clear consent, privacy,
                provider-handling and data-sovereignty arrangements.
              </p>
            </article>
          </div>
        </section>

        <section
          className="how-production how-narrative"
          aria-labelledby="how-production-title"
        >
          <article className="how-narrative-row">
            <h2 id="how-production-title">Prototype to production</h2>
            <div className="how-narrative-copy">
              <p>
                A competition prototype, not a finished service. This standalone
                website exists so judges can see one synthetic, end-to-end case
                working for the Build a Bureaucrat Bot competition. It should not
                become another portal for applicants or assessors.
              </p>

              <div
                className="how-production-chain"
                aria-label="Production direction: application, then an advisory AI check, then the Grant Management Unit"
              >
                <strong>Application</strong>
                <b aria-hidden="true">→</b>
                <strong>Advisory AI check</strong>
                <b aria-hidden="true">→</b>
                <strong>Grant Management Unit</strong>
              </div>

              <p>
                Writer guidance belongs inside the application form, while
                assessor findings belong inside the existing grant-management
                workflow. The original application and every decision stay with
                people, and an AI failure must never prevent an application from
                continuing.
              </p>
              <p>
                <strong>Grant-program agnostic has to be earned. </strong>
                Replaceable documents show how another rulebook could be loaded;
                they do not prove consistent performance. That requires testing
                across programs with different rules, forms, budgets, attachments
                and language, measuring both missed issues and false alarms.
              </p>
              <p>
                <strong>Production needs accountable people, not just more code. </strong>
                Applicants, grant teams and First Nations communities would need
                to shape and test the service. Named owners would also be needed
                for grant rules, model changes, privacy and security assurance,
                cultural consultation, quality monitoring and disputed findings.
              </p>
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}
