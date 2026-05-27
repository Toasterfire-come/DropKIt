remove // SUPPORT US tag
start bar at 0$ instead of 5000
fix rotatiing sponsor wheel Sponsor 4
Sponsor 5Sponsor 1Sponsor 2Sponsor 3Sponsor 4 to only show Sponsors & Partners Go Here with the same graphic
 
TASK: DropKit – seed first project (SafeKeyVault) so it actually renders,
       and harden frontend⇄backend connectivity across all environments
       (local Mac dev, dropkit.me production tunnel).



== PART A — SafeKeyVault must show on the homepage and project pages ==

Source of truth for project content:
  - https://github.com/Toasterfire-come/SafeKeyVault  (README for narrative)
  - https://raw.githubusercontent.com/Toasterfire-come/SafeKeyVault/main/Hardware/BOM.csv

.

Required behavior:
  1. backend/seed_projects.py must idempotently upsert SafeKeyVault on every
     startup, set isActive=True for SafeKeyVault, and deactivate any other
     active project so there is exactly ONE active project.
  2. cycleMonth / cycleYear should be set to the current month/year on every
     seed run so it appears as the "current" project.
  3. stockCount must default to a positive value (e.g. 100) on first insert
     but NEVER be overwritten on subsequent boots.
  4. componentsPreview must start with these two lines in this order:
        "1× custom SafeKeyVault PCB (assembled)"
        "2-part 3D-printed enclosure shell"
     followed by the key BOM highlights from Hardware/BOM.csv (MCU, ATECC608A,
     2× W25Q128JV flash, USB-C + USBLC6, 2× APA102 LEDs, TTP223, AMS1117-3.3,
     16 MHz crystal).
  5. imageUrl = the PCB render URL above.
  6. additionalImages = the three README screenshot URLs
     (a55a89b5..., b230057c..., 30a0be83... at github.com/user-attachments).
  7. description = the README intro, lightly cleaned (typos fixed, no
     hallucinations).

Verification — the agent MUST curl these after restart and confirm a real
JSON body (not 404, not empty list):
   curl $BACKEND/api/projects/current
   curl $BACKEND/api/projects
And then load these pages and confirm SafeKeyVault renders with the PCB image:
   /                              (homepage hero, when LAUNCH_MODE=live)
   /apps/makerbox/projects        (catalog card)
   /apps/makerbox/projects/safekeyvault   (detail page with "In the box")

If the homepage hero still doesn't surface SafeKeyVault while
LAUNCH_MODE=waitlist, that's expected (waitlist mode swaps the hero for the
signup form). DO NOT change LAUNCH_MODE without asking.

== PART B — Frontend ⇄ Backend connectivity (must work in 3 envs) ==

Environments:
  1. Local Mac dev:   frontend on http://localhost:3000, backend on
                       http://127.0.0.1:8000 (uvicorn), mongo on localhost.
  2. Production:      cloudflared tunnel "dropkit-tunnel" maps
                       https://dropkit.me/api/*  -> backend:8000
                       https://dropkit.me/*      -> frontend:3000
                       (see /app/cloudflared/config.yml).

Required code state:
  - frontend/src/lib/api.js  axios baseURL must be:
        `${process.env.REACT_APP_BACKEND_URL || ""}/api`
    (relative when env var absent — works for all three ehe nvs uniformly).
  - frontend/src/pages/DevOperationsTab.jsx SSE URL must use the same
    `${REACT_APP_BACKEND_URL || ""}` fallback.
  - frontend/package.json must contain  "proxy": "http://localhost:8000"
    so CRA dev server forwards /api/* to local uvicorn (kills CORS in dev).
  - Grep the whole frontend/src for hardcoded "127.0.0.1", "localhost:8000",
    "localhost:8001", "http://backend", and remove/replace each one with the
    same relative pattern. Report each occurrence found.

Backend CORS (backend/server.py + backend/config.py):
  - CORS_ORIGINS env var must be honoured as a comma-separated list.
  - With allow_credentials=True the wildcard "*" is invalid; the code must
    fall back to explicit origins, not "*".
  - The preview regex (https://.*\.preview\.emergentagent\.com) must stay.
  - Default backend/.env should set
       CORS_ORIGINS=https://dropkit.me,http://localhost:3000,http://127.0.0.1:3000
