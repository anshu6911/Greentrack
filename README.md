## Green Track — Human-Verified Waste Reporting & Cleanup Coordination

### Overview
- **Mission**: empower citizens to report waste, moderators to verify, and volunteers to complete and prove cleanups.
- **Stack**: Flask + SQLite backend (session cookies, image uploads) and responsive HTML/CSS/JS frontend with Font Awesome icons.
- **Highlights**: hero landing, role-based dashboard tabs, moderator queue, volunteer task workflows (claim → progress → proof), analytics cards, and hotspot list.

### Core Features
- Public landing page with hero, “How it Works” cards, animated stats, CTA buttons, and role preview tabs.
- Authentication with email/password for citizen, volunteer, moderator, and admin (session cookie stored server-side).
- Citizen dashboard to submit reports with images, severity, location, optional coordinates, and anonymous flag; status tracker with colored badges.
- Moderator dashboard with pending queue (approve/reject + notes), volunteer assignment dropdown, and global task filters (status, category, keyword).
- Volunteer dashboard with search/filterable available tasks, claim/start/complete actions, and proof photo uploader.
- Analytics view with aggregated stats and area hotspots plus API endpoints for reports, tasks, users, and stats.

### Folder Structure
- `backend/`
  - `app.py` Flask server, routes, auth, analytics, file uploads
  - `seed_db.py` seeds users/reports/tasks/proofs
  - `requirements.txt`, `.env.example`, `database.db` (created at runtime)
- `frontend/`
  - `index.html`, `auth.html`, `dashboard.html`
  - `css/style.css`, `js/{main,auth,dashboard}.js`
- `uploads/seed/` sample images referenced by seed data (new uploads stored beside seeds)

### Prerequisites
- Python 3.10+
- pip (bundled with Python)
- (Optional) PowerShell/Terminal for running commands

### Setup
1. `cd backend`
2. `python -m venv venv`
3. Activate the environment  
   - Windows: `venv\Scripts\activate`  
   - macOS/Linux: `source venv/bin/activate`
4. `pip install -r requirements.txt`
5. (Optional) `copy .env.example .env` (or `cp` on macOS/Linux) and adjust `SECRET_KEY`
6. Initialize the database and seed demo data: `python seed_db.py`

### Running the App
- Ensure the virtual environment is active.
- `python app.py`
- Open `http://localhost:5000` in your browser (Flask serves the frontend directly).
- Uploaded files are written to `uploads/`, max 5 MB, JPG/PNG only.

### Default Test Accounts (from seed script)
- Citizen 1 — `citizen1@example.com` / `password123`
- Citizen 2 — `citizen2@example.com` / `password123`
- Volunteer A — `volunteer1@example.com` / `password123`
- Volunteer B — `volunteer2@example.com` / `password123`
- Moderator — `moderator@example.com` / `password123`

### Demo Script (≈4 minutes)
1. **Citizen report**: login as `citizen1`, open Citizen tab, submit a report (photo + description + severity). Observe it appear in “My Reports” as Pending.
2. **Moderator verify**: logout, login as `moderator`, open Moderator tab → Pending Reports → review the new report → add notes → Mark Valid → assign to Volunteer A via dropdown. Check Global Task List filters.
3. **Volunteer cleanup**: login as `volunteer1`, open Volunteer tab → available tasks → claim assigned report → mark In Progress → Complete and upload a proof photo.
4. **Citizen confirmation**: login again as `citizen1`, view the updated status (Completed) and proof note in “My Reports”. Open Admin tab (if admin/moderator) to verify analytics counters incremented.

### API Highlights
- `POST /api/register`, `POST /api/login`, `POST /api/logout`, `GET /api/me`
- `POST /api/reports`, `GET /api/reports/my`, `GET /api/reports/pending`, `POST /api/reports/<id>/validate`, `POST /api/reports/<id>/assign`
- `GET /api/tasks/available`, `GET /api/tasks/my`, `POST /api/tasks/<id>/{claim|start|complete}`
- `GET /api/tasks/manage` (moderator/admin filters), `GET /api/users/volunteers`, `GET /api/stats`

### Testing Checklist
- [ ] `python app.py` starts without errors and auto-creates `database.db`
- [ ] Register/login flows create sessions and gate role-based tabs
- [ ] Citizen can upload a report image (<=5 MB) and see it in “My Reports”
- [ ] Moderator validates/assigns from the queue; assignments populate volunteer dropdown
- [ ] Volunteer claims, starts, completes with proof upload; task/report status propagate
- [ ] Analytics cards update (completed tasks, verified reports, volunteers count)
- [ ] Seed images load from `uploads/seed/` and new uploads appear in `uploads/`

### Notes
- Set `SECRET_KEY` in production and consider moving SQLite file outside the repo.
- `seed_db.py` clears existing tables before re-populating; run only in dev/demo environments.
- The Flask server enables CORS with credentials, so the standalone frontend and backend can still communicate if deployed separately.

### dark mode added
### dark mode added on dasboard
### photos is uploadin in volunteer dasboard 
### added reward system git add .
git commit -m "updated something"
git push