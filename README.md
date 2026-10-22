# KAYVAK Laptop Health Check

A laptop health monitoring and fault-detection system for non-technical laptop owners.
It gives advice only. It never repairs anything. It can read real values from a Windows
laptop (`collect_windows`) or use simulated demo values (`simulate_health`). The dashboard
and the printed report always say which one the reading came from. This version uses simulated readings.

## Run it

Backend (in `backend`, two terminals). Terminal 1:

```
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

```

Frontend (in `frontend`, a third terminal):

    npm install
    npm run dev

Terminal 2, pick ONE data source:

```
python manage.py collect_windows          # real readings from this Windows laptop
python manage.py simulate_health          # demo values, any computer
```

## Tests

```
cd backend
python manage.py test sensors
```

## How it works (MAPE-K)

- Monitor: a reading of battery, drive, licence and security is stored.
- Analyse: `backend/sensors/analysis.py` compares it with safe limits.
- Plan: the advice for each problem is chosen there too.
- Execute: the dashboard shows the result and a printable report. Nothing is repaired.
- Knowledge: the limits and every past reading are kept in the database.
## Requirements traceability

Requirement numbers come from the Requirements Elicitation Report.

| Requirement | Priority | Where it is built | Tested |
|---|---|---|---|
| FR-01 overall status | Must | `analysis.py` (`analyse`) | `tests.py` |
| FR-02 battery health | Must | `collect_windows.py` (`read_battery`), `analysis.py` | `tests.py` |
| FR-03 drive health | Must | `collect_windows.py` (`read_drive`), `analysis.py` | `tests.py` |
| FR-04 software or hardware, malware | Must | `analysis.py` (`type`), `read_malware` | `tests.py` |
| FR-05 licence alert | Should | `read_licence`, `analysis.py` | `tests.py` |
| FR-06 plain language | Must | `analysis.py` (`explanation`) | `tests.py` |
| FR-07 evidence for each problem | Must | `analysis.py` (`evidence`) | `tests.py` |
| FR-08 technician or self-fix advice | Should | `analysis.py` (`advice`) | `tests.py` |
| FR-09 colour and text label | Must | `statusStyles.js`, `FindingCard.jsx` | by eye |
| FR-10 printable report | Should | `PrintReport.jsx` | by eye |
| FR-11 care guidance | Should | `careTips.js` | by eye |
| FR-12 repair cost range | Could | not built (no technician price data) | - |
| FR-13 text message summary | Could | not built | - |
| NFR-01 usability | Must | not yet tested with 5 users | - |
| NFR-02 privacy | Must | `ConsentGate.jsx`; data stays on the laptop; no ads | by eye |
| NFR-03 performance (60 s) | Should | `collect_windows.py` times each check | `tests.py` (timing is saved) |
| NFR-04 accuracy (90%) | Must | `test_accuracy.py` (cases written by us, not yet by a technician) | `test_accuracy.py` |
| NFR-05 core checks need no internet | Should | all checks run locally | by use |
| NFR-06 Windows 10 and 11 | Must | PowerShell and `powercfg` collector | tested on one laptop only |
| NFR-07 reports only for the user's account | Should | not built | - |