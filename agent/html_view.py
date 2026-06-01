from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import quote


class HTMLViewModule:
    def render_app_page(self) -> str:
        placeholder = "I need to prepare for a reinforcement learning exam in 5 days."
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Study Planning Agent</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <nav class="floating-nav" aria-label="Main navigation">
    <div class="floating-nav-shell">
      <a class="brand-mark" href="#top" data-scroll-top aria-label="Back to top">
        <span class="brand-icon" aria-hidden="true">SP</span>
        <span class="brand-name">Study Planning Agent</span>
      </a>
      <div class="floating-nav-links" aria-label="Page sections">
        <a href="#create-section">Create</a>
        <a href="#latest-section">Latest</a>
        <a href="#history-section">History</a>
        <a href="#architecture-section">Architecture</a>
      </div>
      <button
        id="back-to-top-button"
        class="back-top-button"
        type="button"
        aria-label="Back to top"
      >
        Top
      </button>
    </div>
  </nav>
  <main class="page">
    <section class="hero-card">
      <div class="hero-topline">
        <div class="hero-copy">
          <p class="eyebrow">COMPSCI 767 Assignment 2</p>
          <h1>Study Planning Agent</h1>
          <p class="subtitle">A local intelligent software agent prototype for COMPSCI 767 Assignment 2</p>
          <p class="hero-description">
            Generate study plans, revise them with feedback, and track task progress through a local
            browser interface backed by a modular software agent pipeline.
          </p>
        </div>
      </div>
      <div class="hero-badge-row" aria-label="Agent modules">
        <span class="hero-badge">Perception</span>
        <span class="hero-badge">Decision</span>
        <span class="hero-badge">Action</span>
        <span class="hero-badge">Memory</span>
        <span class="hero-badge">Web Output</span>
      </div>
    </section>

    <section id="message" class="status hidden" aria-live="polite"></section>

    <section id="create-section" class="section-card">
      <div class="section-head">
        <div>
          <p class="section-label">Create</p>
          <h2>Create a Study Plan</h2>
          <p class="section-support">
            Describe the topic and timeline. The agent will infer the study window, task type,
            and planning strategy from your goal.
          </p>
        </div>
      </div>
      <label class="input-label" for="goal-input">Study goal</label>
      <textarea id="goal-input" placeholder="{placeholder}"></textarea>
      <div class="actions">
        <button id="create-button" type="button">Generate Plan</button>
      </div>
    </section>

    <section id="latest-section" class="section-card">
      <div class="section-head">
        <div>
          <p class="section-label">Latest Result</p>
          <h2>Latest Plan</h2>
          <p class="section-support">
            Review the current perceived state, planning strategy, task progress, and revision notes.
          </p>
        </div>
      </div>
      <div id="latest-plan" class="empty-state">
        No study plan has been generated yet.
      </div>
    </section>

    <section id="history-section" class="section-card">
      <div class="section-head">
        <div>
          <p class="section-label">History</p>
          <h2>Planning History</h2>
          <p class="section-support">
            Review plan records, check progress, and reopen the interactive editor without
            leaving the main page.
          </p>
        </div>
      </div>
      <div id="history-list" class="history-grid">
        <div class="empty-state">No planning history yet.</div>
      </div>
      <div id="history-controls" class="history-controls hidden">
        <button id="load-more-button" class="secondary-button" type="button">Load More</button>
      </div>
    </section>

    <section id="architecture-section" class="section-card">
      <div class="section-head">
        <div>
          <p class="section-label">Architecture</p>
          <h2>Agent Architecture</h2>
          <p class="section-support">
            The browser handles interaction and task state updates, while the agent modules
            interpret goals, revise the current plan, and persist records into plans.js.
          </p>
        </div>
      </div>
      <div class="architecture-flow" aria-label="Agent pipeline">
        <span class="architecture-step">Browser UI</span>
        <span class="architecture-arrow">&rarr;</span>
        <span class="architecture-step">Local Server</span>
        <span class="architecture-arrow">&rarr;</span>
        <span class="architecture-step">Perception</span>
        <span class="architecture-arrow">&rarr;</span>
        <span class="architecture-step">Decision</span>
        <span class="architecture-arrow">&rarr;</span>
        <span class="architecture-step">Action</span>
        <span class="architecture-arrow">&rarr;</span>
        <span class="architecture-step">Memory</span>
      </div>
      <p class="architecture-note">
        Every plan request flows through the local HTTP server into the agent pipeline, then
        returns to the browser as rendered plan data loaded from <code>web/data/plans.js</code>.
      </p>
    </section>
  </main>

  <footer class="footer">
    Local prototype for COMPSCI 767 Assignment 2
  </footer>

  <div id="record-modal" class="modal hidden" aria-hidden="true">
    <div class="modal-backdrop" id="record-modal-backdrop"></div>
    <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="record-modal-title">
      <button id="record-modal-close" class="modal-close" type="button" aria-label="Close details">&times;</button>
      <div id="record-modal-content"></div>
    </div>
  </div>

  <script src="/data/plans.js"></script>
  <script src="/static/app.js"></script>
</body>
</html>
"""

    def render_record_page(self, record: dict[str, Any]) -> str:
        plan = record.get("plan") if isinstance(record.get("plan"), dict) else {}
        perceived_state = (
            record.get("perceived_state") if isinstance(record.get("perceived_state"), dict) else {}
        )
        record_id = str(record.get("id", ""))
        task_type = self._text(perceived_state.get("task_type"), "study plan")
        latest_feedback = self._text(record.get("latest_feedback"))
        update_history = self._render_update_history(record.get("update_history"))

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{self._text(plan.get("title"), "Study Plan Record")} | Study Planning Agent</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body class="detail-page">
  <main class="page detail-page-shell">
    <section class="hero-card detail-hero-card">
      <div class="detail-header-top">
        <div class="detail-header-copy">
          <p class="eyebrow">Plan Record Fallback View</p>
          <h1 class="detail-page-title">{self._text(plan.get("title"), "Study Plan")}</h1>
          <p class="subtitle">
            Full study plan details rendered directly from <code>web/data/plans.js</code>.
          </p>
        </div>
        <div class="detail-actions">
          <a class="button-link" href="/">&larr; Back to Agent</a>
          <a class="button-link button-link-secondary" href="/api/record?id={quote(record_id)}" target="_blank" rel="noopener">Download JSON</a>
        </div>
      </div>

      <div class="plan-badge-row">
        <span class="task-badge">{task_type}</span>
      </div>

      <div class="detail-meta-grid">
        <article class="summary-tile">
          <span class="meta-label">Record ID</span>
          <strong>{self._text(record_id)}</strong>
        </article>
        <article class="summary-tile">
          <span class="meta-label">Created</span>
          <strong>{self._text(record.get("created_at"))}</strong>
        </article>
        <article class="summary-tile">
          <span class="meta-label">Last Updated</span>
          <strong>{self._text(record.get("updated_at"), self._text(record.get("created_at")))}</strong>
        </article>
        <article class="summary-tile detail-wide">
          <span class="meta-label">Goal</span>
          <strong>{self._text(record.get("goal"))}</strong>
        </article>
      </div>
    </section>

    <section class="section-card">
      <div class="section-head">
        <div>
          <p class="section-label">Perception</p>
          <h2>Perceived State</h2>
        </div>
      </div>
      <div class="summary-grid">
        <article class="summary-tile">
          <span class="meta-label">Topic</span>
          <strong>{self._text(perceived_state.get("topic"))}</strong>
        </article>
        <article class="summary-tile">
          <span class="meta-label">Days</span>
          <strong>{self._text(perceived_state.get("days"))}</strong>
        </article>
        <article class="summary-tile">
          <span class="meta-label">Difficulty</span>
          <strong>{self._text(perceived_state.get("difficulty"))}</strong>
        </article>
        <article class="summary-tile">
          <span class="meta-label">Task Type</span>
          <strong>{task_type}</strong>
        </article>
      </div>
    </section>

    <section class="section-card">
      <div class="section-head">
        <div>
          <p class="section-label">Decision</p>
          <h2>Plan Overview</h2>
        </div>
      </div>
      <div class="plan-detail-grid">
        <section class="detail-panel detail-panel-wide">
          <h4>Summary</h4>
          <p>{self._text(plan.get("summary"))}</p>
        </section>

        <section class="detail-panel">
          <h4>Strategy</h4>
          <p>{self._text(plan.get("strategy"))}</p>
        </section>

        <section class="detail-panel">
          <h4>Priority List</h4>
          {self._render_list(plan.get("priority_list"), empty_text="No priorities recorded.")}
        </section>

        <section class="detail-panel">
          <h4>Study Notes</h4>
          {self._render_list(plan.get("study_notes"), empty_text="No study notes recorded.")}
        </section>

        <section class="detail-panel risk-panel">
          <h4>Risk Warning</h4>
          <p>{self._text(plan.get("risk_warning"))}</p>
        </section>
      </div>
    </section>

    <section class="section-card section-card-accent">
      <div class="section-head">
        <div>
          <p class="section-label">Revision Memory</p>
          <h2>Feedback and Update History</h2>
        </div>
      </div>
      <div class="plan-detail-grid">
        <section class="detail-panel">
          <h4>Latest Feedback</h4>
          <p>{latest_feedback or "No feedback provided yet."}</p>
        </section>
        <section class="detail-panel">
          <h4>Update History</h4>
          {update_history}
        </section>
      </div>
    </section>

    <section class="section-card">
      <div class="section-head">
        <div>
          <p class="section-label">Action</p>
          <h2>Daily Tasks</h2>
        </div>
      </div>
      <div class="days-grid">
        {self._render_days(plan.get("daily_tasks"))}
      </div>
    </section>
  </main>
</body>
</html>
"""

    def render_record_not_found_page(self, record_id: str, message: str, status_label: str = "Record Error") -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(status_label)} | Study Planning Agent</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body class="detail-page">
  <main class="page detail-page-shell">
    <section class="hero-card detail-hero-card">
      <p class="eyebrow">{escape(status_label)}</p>
      <h1 class="detail-page-title">Could not open the requested record</h1>
      <p class="subtitle">The browser requested a record detail page, but no matching JSON record was found.</p>
      <div class="detail-actions">
        <a class="button-link" href="/">&larr; Back to Agent</a>
      </div>
    </section>

    <section class="section-card">
      <div class="detail-panel detail-panel-wide">
        <h4>Requested record</h4>
        <p>{escape(record_id or "No record id provided.")}</p>
        <h4>Error</h4>
        <p>{escape(message)}</p>
      </div>
    </section>
  </main>
</body>
</html>
"""

    def _render_list(self, values: Any, empty_text: str) -> str:
        items = values if isinstance(values, list) else []
        if not items:
            return f'<p class="muted">{escape(empty_text)}</p>'

        rendered_items = "".join(
            f"<li>{escape(self._list_item_text(item))}</li>"
            for item in items
            if self._list_item_text(item)
        )
        if not rendered_items:
            return f'<p class="muted">{escape(empty_text)}</p>'
        return f'<ul class="bullet-list spacious-list">{rendered_items}</ul>'

    def _render_days(self, values: Any) -> str:
        days = values if isinstance(values, list) else []
        if not days:
            return '<div class="empty-state">No daily tasks recorded.</div>'

        cards: list[str] = []
        for index, raw_day in enumerate(days, start=1):
            if not isinstance(raw_day, dict):
                continue

            if "day_number" in raw_day or "title" in raw_day:
                day_number = raw_day.get("day_number", index)
                focus = raw_day.get("title") or raw_day.get("focus") or f"Day {index}"
                objective = raw_day.get("focus") or raw_day.get("objective") or ""
            else:
                day_number = raw_day.get("day", index)
                focus = raw_day.get("focus") or f"Day {index}"
                objective = raw_day.get("objective") or ""

            tasks = raw_day.get("tasks")
            tasks_html = self._render_list(tasks, empty_text="No tasks recorded.")
            cards.append(
                f"""
        <article class="day-card">
          <span class="day-label">Day {escape(str(day_number))}</span>
          <h5 class="day-title">{escape(str(focus))}</h5>
          <p class="day-focus">{escape(str(objective))}</p>
          {tasks_html}
        </article>
"""
            )

        return "".join(cards) or '<div class="empty-state">No daily tasks recorded.</div>'

    def _kind_badge_class(self, kind: Any) -> str:
        value = str(kind or "created").lower()
        if value == "updated":
            return "kind-badge kind-badge-updated"
        return "kind-badge kind-badge-created"

    def _kind_label(self, kind: Any) -> str:
        return escape(str(kind or "created").upper())

    def _render_update_history(self, values: Any) -> str:
        entries = values if isinstance(values, list) else []
        if not entries:
            return '<p class="muted">No feedback revisions recorded yet.</p>'

        cards: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            timestamp = self._text(entry.get("timestamp"))
            feedback = self._text(entry.get("feedback"))
            if not feedback:
                continue
            cards.append(
                f"""
        <article class="update-history-item">
          <p class="meta-label">{timestamp}</p>
          <p>{feedback}</p>
        </article>
"""
            )
        return f'<div class="update-history-list">{"".join(cards)}</div>' if cards else '<p class="muted">No feedback revisions recorded yet.</p>'

    def _list_item_text(self, item: Any) -> str:
        if isinstance(item, dict):
            return str(item.get("text") or item.get("task") or "")
        return str(item)

    def _text(self, value: Any, fallback: str = "") -> str:
        text = str(value or fallback)
        return escape(text)
