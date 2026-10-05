# IT Asset Management Dashboard

A web dashboard for IT teams to track company hardware (laptops, desktops, monitors)
and keep a full audit trail of every transfer between IT stock and employees.

## Features
- Asset inventory with search, filters, and CSV export
- Transfer log: who gave, who received, which IT staff member handled it, and when
- Repair and retirement tracking (retired assets are locked, history is kept)
- Summary cards and charts by status, condition, item type, and department
- Input validation and parameterized SQL queries

## Tech Stack
- **Backend:** Python, FastAPI, pyodbc
- **Database:** Microsoft SQL Server
- **Frontend:** HTML, CSS, JavaScript, Chart.js

## Run locally
1. Install SQL Server (Express is fine) and the ODBC Driver 18 for SQL Server
2. Run `database/schema.sql` in SQL Server Management Studio
3. Copy `backend/.env.example` to `backend/.env` and set your server name
4. In the `backend` folder, install the packages:

        pip install -r requirements.txt

5. Start the server:

        uvicorn main:app --reload

6. Open http://localhost:8000

On Windows you can also double-click `start.bat` after completing steps 1-4.

## Project structure
- `backend/` FastAPI application
- `frontend/` Dashboard page
- `database/` SQL schema
