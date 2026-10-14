# KAYVAK Laptop Health Check

A laptop health monitoring and fault-detection system for non-technical laptop owners.
It gives advice only. It never repairs anything. This version uses simulated readings.

## Run it

Backend (in `backend`, three commands in two terminals):

```
python manage.py migrate
python manage.py simulate_health
python manage.py runserver
```

Frontend (in `frontend`):

```
npm install
npm run dev
```

Open the address that Vite prints (usually http://localhost:5173).

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