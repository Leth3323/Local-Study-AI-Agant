# Study Planning Agent

## Project Title

Study Planning Agent: A Local Intelligent Software Agent Prototype for COMPSCI 767 Assignment 2

## Project Overview

This project is a local browser-based intelligent software agent prototype for COMPSCI 767. It acts as a Personal Task Planning Agent: the user enters a study or task goal, the agent interprets the goal, creates a structured plan, stores the plan locally, and allows the plan to be revised from feedback.

The current prototype focuses on study planning. It can infer a topic, duration, task type, and difficulty level from a user goal, then produce a day-by-day schedule with actionable tasks. Users can edit progress in the browser by marking tasks as `To Do`, `In Progress`, or `Done`.

## Features

- Parse a natural-language study goal into perceived state.
- Generate a structured daily plan with summary, strategy, priorities, risks, and study notes.
- Update an existing plan based on feedback, including timeline changes such as extending a 3-day plan to 5 days.
- Track task progress with persistent task statuses.
- View and edit plans in an in-page detail modal.
- Delete local plan records from the browser interface.
- Store generated records locally in `web/data/plans.js`.
- Run entirely with Python standard library modules.
- Use a local browser UI with no external service dependency.

## System Design

The system follows a modular intelligent-agent pipeline:

- `PerceptionModule`: interprets the raw user goal and extracts topic, duration, difficulty, and task type.
- `DecisionModule`: creates or revises the plan using the perceived state and optional feedback.
- `ActionModule`: packages generated plans into structured records and preserves task status when plans are updated.
- `MemoryModule`: persists plan records and task status updates to local storage files.
- `HTMLViewModule` and `web_server.py`: expose the local browser interface and API routes.
- Frontend files in `web/`: render records, handle modal editing, update task statuses, and call the local API.

More design notes are available in `docs/system_design.md`.

## Technologies Used

- Python 3
- Python standard library only
  - `http.server`
  - `json`
  - `pathlib`
  - `re`
  - `dataclasses`
  - `unittest`
- HTML
- CSS
- Vanilla JavaScript

No external Python packages are required for the current prototype.

## Installation Instructions

1. Clone the repository:

   ```bash
   git clone https://github.com/Leth3323/A-local-intelligent-software-agent-prototype-for-COMPSCI-767-Assignment-2.git
   cd A-local-intelligent-software-agent-prototype-for-COMPSCI-767-Assignment-2
   ```

2. Confirm Python is installed:

   ```bash
   python --version
   ```

   If your system uses `python3`, use `python3` in the commands below.

3. Optional: create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   The current `requirements.txt` documents that no external dependencies are needed.

## How to Run

Start the local web app:

```bash
python main.py
```

Then open:

```text
http://localhost:8000
```

The app runs locally on port `8000`.

## How to Use

1. Enter a goal in the `Create a Study Plan` section.
2. Click `Generate Plan`.
3. Review the latest plan, including perceived state, strategy, progress, daily tasks, and risk warning.
4. Click `View / Edit` to open the detail modal.
5. Change individual task statuses using `To Do`, `In Progress`, and `Done`.
6. Add feedback in the modal update panel, such as:

   ```text
   I now need to extend my study time to five days.
   ```

7. Click `Update Plan` to revise the same plan record.
8. Use the history section to reopen earlier plans.
9. Use `Delete` if you want to remove a local plan record.

## Demo Video

Demo video: https://youtu.be/ddgtlx5cDr8

## Assignment Output Notes

- GitHub repository: https://github.com/Leth3323/A-local-intelligent-software-agent-prototype-for-COMPSCI-767-Assignment-2
- Demo video: https://youtu.be/ddgtlx5cDr8
- Two-page report draft: `docs/report.md`
- Printable HTML report: `docs/report.html`
- The prototype demonstrates a local intelligent-agent workflow: perception, decision-making, action, and memory.
- The app stores runtime-generated plans locally and does not require API keys, cloud services, or a database.
- Screenshots for the final report can be inserted into the placeholder sections in `docs/report.md` or `docs/report.html`.

## Project Structure

```text
.
├── agent/
│   ├── action.py
│   ├── agent.py
│   ├── decision.py
│   ├── html_view.py
│   ├── memory.py
│   └── perception.py
├── data/
│   └── sample_goals.txt
├── docs/
│   ├── report.html
│   ├── report.md
│   ├── report_notes.md
│   └── system_design.md
├── tests/
│   └── test_agent_behaviour.py
├── web/
│   ├── app.js
│   ├── data/
│   │   └── .gitkeep
│   └── style.css
├── main.py
├── requirements.txt
├── view_site.py
├── web_server.py
├── .gitignore
└── README.md
```

## Notes for Reproduction

- This project stores local generated plan records in `web/data/plans.js` at runtime.
- Legacy local memory may be stored in `data/memory.json`.
- These runtime data files are intentionally excluded from Git so each user can generate fresh local plans.
- If `web/data/plans.js` does not exist, the app creates it automatically when the server starts.
- The project is intended to run locally and does not require API keys, cloud services, or a database.
- Run the basic test suite with:

  ```bash
  python -m unittest discover -s tests -v
  ```
