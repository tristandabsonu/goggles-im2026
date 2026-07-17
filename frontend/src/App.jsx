import { useEffect, useRef, useState } from "react";

import logoImage from "./assets/logo.png";
import AssessorView from "./views/AssessorView";
import ExampleResultsView from "./views/ExampleResultsView";
import ForDevsView from "./views/ForDevsView";
import HowItWorksView from "./views/HowItWorksView";
import ApplicantView from "./views/ApplicantView";

function HeroArt() {
  return (
    <div className="hero-art" aria-hidden="true">
      <div className="markup-motif">
        <span className="markup-lines" />
        <svg viewBox="0 0 700 430">
          <path
            className="markup-circle"
            d="M180 119 C280 58 493 65 557 151 C611 224 526 295 361 300 C210 305 112 248 127 177 C134 145 151 130 180 119 Z"
          />
          <path
            className="markup-underline"
            d="M190 247 C293 260 405 251 516 239"
          />
          <path
            className="markup-arrow"
            d="M571 88 C622 122 625 177 589 211 M589 211 L590 180 M589 211 L617 198"
          />
        </svg>
        <span className="markup-dot" />
        <span className="markup-reference">verify · Section 5.4</span>
      </div>
    </div>
  );
}

function SiteHeader({ activePage }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return undefined;

    const closeOnEscape = (event) => {
      if (event.key !== "Escape") return;
      setMenuOpen(false);
      menuButtonRef.current?.focus();
    };

    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [menuOpen]);

  useEffect(() => {
    const desktopNav = window.matchMedia("(min-width: 801px)");
    const closeAtDesktop = (event) => {
      if (event.matches) setMenuOpen(false);
    };

    desktopNav.addEventListener("change", closeAtDesktop);
    return () => desktopNav.removeEventListener("change", closeAtDesktop);
  }, []);

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="site-header">
        <div className="nav-inner">
          <a className="brand" href="/" aria-label="GOGgles home">
            <img className="brand-logo" src={logoImage} alt="" />
            <span>
              <strong>GOGgles</strong>
              <small>IM2026</small>
            </span>
          </a>
          <button
            ref={menuButtonRef}
            type="button"
            className="menu-toggle"
            aria-expanded={menuOpen}
            aria-controls="main-navigation"
            aria-label={menuOpen ? "Close main navigation" : "Open main navigation"}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="menu-toggle-lines" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
          </button>
          <nav
            id="main-navigation"
            className={`main-nav${menuOpen ? " is-open" : ""}`}
            aria-label="Main navigation"
            onClick={(event) => {
              if (event.target.closest("a")) setMenuOpen(false);
            }}
          >
            <a
              className={activePage === "home" ? "active" : ""}
              href="/"
              aria-current={activePage === "home" ? "page" : undefined}
            >
              Home
            </a>
            <a
              className={activePage === "how" ? "active" : ""}
              href="/how-it-works"
              aria-current={activePage === "how" ? "page" : undefined}
            >
              How it works
            </a>
            <a
              className={activePage === "examples" ? "active" : ""}
              href="/example-results"
              aria-current={activePage === "examples" ? "page" : undefined}
            >
              Example results
            </a>
          </nav>
        </div>
      </header>
    </>
  );
}

function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <strong>GOGgles IM2026</strong>
          <span>Grant guidance, with the source in sight.</span>
        </div>
        <nav aria-label="Footer navigation">
          <a href="/">Home</a>
          <a href="/how-it-works">How it works</a>
          <a href="/example-results">Example results</a>
        </nav>
        <p>
          Developer: {" "}
          <a
            href="https://au.linkedin.com/in/tristandabsonu"
            target="_blank"
            rel="noreferrer"
            aria-label="Tristan Garcia on LinkedIn (opens in a new tab)"
          >
            Tristan Garcia
          </a>
        </p>
      </div>
    </footer>
  );
}

function HomePage() {
  const [view, setView] = useState("applicant");

  useEffect(() => {
    if (window.location.hash !== "#try-it-now") return;
    window.requestAnimationFrame(() => {
      document.getElementById("try-it-now")?.scrollIntoView();
    });
  }, []);

  return (
    <div className="site-shell">
      <SiteHeader activePage="home" />
      <main id="main-content" tabIndex={-1}>
        <div className="view-switcher">
          <div
            className="view-tabs"
            role="group"
            aria-label="Choose a GOGgles view"
          >
            <button
              type="button"
              className={view === "applicant" ? "active" : ""}
              aria-pressed={view === "applicant"}
              onClick={() => setView("applicant")}
            >
              <span>Applicant</span>
              <small>Build and check a draft</small>
            </button>
            <button
              type="button"
              className={view === "assessor" ? "active" : ""}
              aria-pressed={view === "assessor"}
              onClick={() => setView("assessor")}
            >
              <span>Assessor</span>
              <small>Review a submitted grant proposal</small>
            </button>
          </div>
        </div>
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <span className="eyebrow">
                Grant guidance, with the source in sight
              </span>
              {view === "applicant" ? (
                <>
                  <h1>Good work shouldn't lose on the paperwork.</h1>
                  <p>
                    GOGgles checks selected draft answers against the supplied
                    grant guidance, shows the relevant source and suggests what
                    you could address. You remain the author and decide what to
                    change.
                  </p>
                </>
              ) : (
                <>
                  <h1>
                    Put judgement back at the centre of grant assessment.
                  </h1>
                  <p>
                    GOGgles finds supported mechanical issues in a submitted
                    proposal and shows the relevant sources, so assessors can
                    focus on merit, evidence and local context. Every judgement
                    remains with a person.
                  </p>
                </>
              )}
              <div className="hero-actions">
                <a className="hero-cta" href="/how-it-works">
                  See how it works
                </a>
                <a
                  className="hero-cta hero-cta-secondary"
                  href="#try-it-now"
                >
                  Try it now
                  <span aria-hidden="true">↓</span>
                </a>
              </div>
            </div>
            <HeroArt />
          </div>
        </section>
        <section
          id="try-it-now"
          className="working-view"
          aria-label={`${view === "assessor" ? "Assessor" : "Applicant"} view`}
        >
          {view === "assessor" ? <AssessorView /> : <ApplicantView />}
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

function HowItWorksPage() {
  return (
    <div className="site-shell">
      <SiteHeader activePage="how" />
      <HowItWorksView />
      <SiteFooter />
    </div>
  );
}

function ExampleResultsPage() {
  return (
    <div className="site-shell">
      <SiteHeader activePage="examples" />
      <ExampleResultsView />
      <SiteFooter />
    </div>
  );
}

function ForDevsPage() {
  return (
    <div className="site-shell">
      <SiteHeader activePage="" />
      <ForDevsView />
      <SiteFooter />
    </div>
  );
}

export default function App() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";

  useEffect(() => {
    const pageTitles = {
      "/how-it-works": "How it works | GOGgles IM2026",
      "/example-results": "Example results | GOGgles IM2026",
      "/for-devs": "For the devs | GOGgles IM2026",
    };
    document.title = pageTitles[path] || "GOGgles IM2026";
  }, [path]);

  if (path === "/how-it-works") return <HowItWorksPage />;
  if (path === "/example-results") return <ExampleResultsPage />;
  if (path === "/for-devs") return <ForDevsPage />;
  return <HomePage />;
}
