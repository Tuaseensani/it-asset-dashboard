from pathlib import Path
from typing import Literal, Optional
import pyodbc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from database import get_connection, get_db_cursor
import uvicorn

app = FastAPI(title="IT Assets Management API")

# Enable CORS for frontend integration (VS Code Live Server & direct host)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_query(sql: str, params: tuple | list = None):
    """
    Executes a SELECT query and returns rows as a list of dictionaries.
    Uses context manager for safe connection and cursor lifecycle management.
    """
    with get_db_cursor() as cursor:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

# --- Pydantic Models ---
class NewAsset(BaseModel):
    ItemType: str
    Brand: Optional[str] = None
    Model: Optional[str] = None
    SerialNo: str
    Memory: Optional[str] = None
    Storage: Optional[str] = None
    Processor: Optional[str] = None
    Condition: Literal["New", "Good", "Fair", "Poor"]

class AssetUpdate(BaseModel):
    Brand: Optional[str] = None
    Model: Optional[str] = None
    Memory: Optional[str] = None
    Storage: Optional[str] = None
    Processor: Optional[str] = None
    Condition: Optional[Literal["New", "Good", "Fair", "Poor"]] = None
    Status: Optional[Literal["Under Repair", "Retired", "Active"]] = None

class NewTransfer(BaseModel):
    AssetID: int
    ToEmployeeID: Optional[str] = None   # leave empty to return asset to IT stock
    HandledByID: str
    Notes: Optional[str] = None

# --- API Endpoints ---
@app.get("/assets")
def get_assets():
    try:
        query = """
            SELECT a.AssetID, a.ItemType, a.Brand, a.Model, a.SerialNo,
                   a.Memory, a.Storage, a.Processor, a.[Condition], a.Status,
                   e.EmployeeID, e.EmployeeName, e.Department, e.Designation, e.Grade,
                   t.TransferDate AS DateIssued
            FROM Assets a
            OUTER APPLY (
                SELECT TOP 1 ToEmployeeID, TransferDate
                FROM AssetTransfers
                WHERE AssetID = a.AssetID
                ORDER BY TransferDate DESC, TransferID DESC
            ) t
            LEFT JOIN Employees e ON e.EmployeeID = t.ToEmployeeID
        """
        return run_query(query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/assets", status_code=201)
def create_asset(asset: NewAsset):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO Assets (ItemType, Brand, Model, SerialNo, Memory, Storage,
                                Processor, [Condition], Status)
            OUTPUT INSERTED.AssetID
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'In Stock')
            """,
            asset.ItemType, asset.Brand, asset.Model, asset.SerialNo,
            asset.Memory, asset.Storage, asset.Processor, asset.Condition,
        )
        new_id = cursor.fetchone()[0]
        conn.commit()
    except pyodbc.IntegrityError:
        raise HTTPException(status_code=409, detail="Serial number already exists")
    finally:
        conn.close()
    return {"AssetID": new_id, "message": "Asset created"}

@app.put("/assets/{asset_id}")
def update_asset(asset_id: int, update: AssetUpdate):
    changes = update.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Nothing to update")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Status FROM Assets WHERE AssetID = ?", asset_id)
        asset = cursor.fetchone()
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        if asset.Status == "Retired":
            raise HTTPException(status_code=400, detail="Retired assets cannot be edited")

        if "Status" in changes and changes["Status"] == "Active":
            cursor.execute(
                """
                SELECT TOP 1 ToEmployeeID FROM AssetTransfers
                WHERE AssetID = ?
                ORDER BY TransferDate DESC, TransferID DESC
                """,
                asset_id,
            )
            last = cursor.fetchone()
            changes["Status"] = "Issued" if last and last.ToEmployeeID else "In Stock"

        set_clause = ", ".join(f"[{col}] = ?" for col in changes)
        cursor.execute(
            f"UPDATE Assets SET {set_clause} WHERE AssetID = ?",
            *changes.values(), asset_id,
        )
        conn.commit()
    finally:
        conn.close()
    return {"message": "Asset updated"}

@app.post("/transfers", status_code=201)
def create_transfer(transfer: NewTransfer):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Status FROM Assets WHERE AssetID = ?", transfer.AssetID)
        asset = cursor.fetchone()
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        if asset.Status == "Retired":
            raise HTTPException(status_code=400, detail="Retired assets cannot be transferred")

        cursor.execute(
            """
            SELECT TOP 1 ToEmployeeID FROM AssetTransfers
            WHERE AssetID = ?
            ORDER BY TransferDate DESC, TransferID DESC
            """,
            transfer.AssetID,
        )
        last = cursor.fetchone()
        current_holder = last.ToEmployeeID if last else None

        if transfer.ToEmployeeID == current_holder:
            raise HTTPException(status_code=400, detail="Asset is already with that holder")

        cursor.execute(
            """
            INSERT INTO AssetTransfers (AssetID, FromEmployeeID, ToEmployeeID, HandledByID, Notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            transfer.AssetID, current_holder, transfer.ToEmployeeID,
            transfer.HandledByID, transfer.Notes,
        )

        new_status = "Issued" if transfer.ToEmployeeID else "In Stock"
        cursor.execute("UPDATE Assets SET Status = ? WHERE AssetID = ?", new_status, transfer.AssetID)

        conn.commit()
    except pyodbc.IntegrityError:
        raise HTTPException(status_code=400, detail="Employee ID not found")
    finally:
        conn.close()
    return {"message": "Transfer recorded", "new_status": new_status}

@app.get("/transfers")
def get_transfers(asset_id: Optional[int] = None):
    try:
        sql = """
            SELECT t.TransferID, t.AssetID, a.ItemType, a.SerialNo,
                   t.FromEmployeeID, f.EmployeeName AS FromName,
                   t.ToEmployeeID, r.EmployeeName AS ToName,
                   t.HandledByID, h.EmployeeName AS HandledByName,
                   t.TransferDate, t.Notes
            FROM AssetTransfers t
            JOIN Assets a ON a.AssetID = t.AssetID
            LEFT JOIN Employees f ON f.EmployeeID = t.FromEmployeeID
            LEFT JOIN Employees r ON r.EmployeeID = t.ToEmployeeID
            JOIN Employees h ON h.EmployeeID = t.HandledByID
        """
        params = []
        if asset_id is not None:
            sql += " WHERE t.AssetID = ?"
            params.append(asset_id)
        sql += " ORDER BY t.TransferDate DESC, t.TransferID DESC"

        return run_query(sql, params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/employees")
def get_employees(department: Optional[str] = None):
    try:
        sql = """
            SELECT EmployeeID, EmployeeName, Department, Designation, Grade
            FROM Employees
        """
        params = []
        if department:
            sql += " WHERE Department = ?"
            params.append(department)
        sql += " ORDER BY EmployeeName"

        return run_query(sql, params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/stats")
def get_stats():
    try:
        total = run_query("SELECT COUNT(*) AS Total FROM Assets")[0]["Total"]

        by_status = run_query(
            "SELECT Status AS Label, COUNT(*) AS Count FROM Assets GROUP BY Status"
        )
        by_condition = run_query(
            "SELECT [Condition] AS Label, COUNT(*) AS Count FROM Assets GROUP BY [Condition]"
        )
        by_item_type = run_query(
            "SELECT ItemType AS Label, COUNT(*) AS Count FROM Assets GROUP BY ItemType"
        )
        by_department = run_query("""
            SELECT ISNULL(e.Department, 'IT Stock') AS Label, COUNT(*) AS Count
            FROM Assets a
            OUTER APPLY (
                SELECT TOP 1 ToEmployeeID
                FROM AssetTransfers
                WHERE AssetID = a.AssetID
                ORDER BY TransferDate DESC, TransferID DESC
            ) t
            LEFT JOIN Employees e ON e.EmployeeID = t.ToEmployeeID
            GROUP BY ISNULL(e.Department, 'IT Stock')
        """)

        return {
            "total": total,
            "by_status": by_status,
            "by_condition": by_condition,
            "by_item_type": by_item_type,
            "by_department": by_department,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
