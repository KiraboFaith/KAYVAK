# KAYVAK Dashboard (frontend)

The web dashboard for the KAYVAK Laptop Health Check. It shows the health readings
collected by the backend in plain words, with a colour and a text label for every
finding, and lets the owner print a report.

Built with React 19, React Router and Vite.

## Run it

The backend must be running first (see the main README in the project root). It is
expected at `http://127.0.0.1:8000`.

```
npm install
npm run dev
```

Then open `http://localhost:5173`. Keep the default port: the backend only accepts
requests from `localhost:5173` and `127.0.0.1:5173` (see `CORS_ALLOWED_ORIGINS` in
`backend/kayvak_backend/settings.py`).

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Starts the development server with hot reload |
| `npm run build` | Builds the app for production |
| `npm run preview` | Serves the production build locally |
| `npm run lint` | Checks the code with ESLint |

## Pages

| Route | Screen |
|---|---|
| `/` | Dashboard: overall status, findings, before/after repair snapshots, shutdown report |
| `/settings` | Notification settings |
| `/keyboard` | Keyboard test |

## Where things are

```
src/
  App.jsx            routes, consent screen and notification prompt
  api.js             apiFetch(): adds the header the backend requires
  careTips.js        care guidance shown to the owner
  statusStyles.js    colour and text label for each status
  notifications.js   notification settings requests
  snapshots.js       before/after snapshot requests
  components/
    ConsentGate.jsx        privacy consent shown on first open
    NotificationGate.jsx   asks about notifications on first open
    Dashboard.jsx          main screen
    FindingCard.jsx        one problem, with evidence and advice
    PrintReport.jsx        printable report
    SnapshotPanel.jsx      before/after repair comparison
    BlackoutPanel.jsx      unexpected shutdown report
    SettingsPanel.jsx      notification settings
    KeyboardTest.jsx       keyboard test
```

## API header

Every request to the backend must carry the `X-Kayvak-Client: dashboard` header. This
blocks other websites open in the same browser from driving the local server. Use
`apiFetch()` from `src/api.js` instead of calling `fetch` directly, so the header is
never forgotten.