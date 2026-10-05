from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field

# Allowed status and condition literals based on SQL Server constraints
ConditionType = Literal["New", "Good", "Fair", "Poor"]
StatusType = Literal["Issued", "In Stock", "Under Repair", "Retired"]

# --- Asset Schemas ---
class AssetBase(BaseModel):
    ItemType: str = Field(..., example="Laptop")
    Brand: Optional[str] = Field(None, example="Dell")
    Model: Optional[str] = Field(None, example="Latitude 5420")
    SerialNo: str = Field(..., example="SN-123456")
    Memory: Optional[str] = Field(None, example="16GB")
    Storage: Optional[str] = Field(None, example="512GB SSD")
    Processor: Optional[str] = Field(None, example="Intel Core i5")
    Condition: Optional[ConditionType] = "Good"
    Status: Optional[StatusType] = "In Stock"

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    ItemType: Optional[str] = None
    Brand: Optional[str] = None
    Model: Optional[str] = None
    SerialNo: Optional[str] = None
    Memory: Optional[str] = None
    Storage: Optional[str] = None
    Processor: Optional[str] = None
    Condition: Optional[ConditionType] = None
    Status: Optional[StatusType] = None

class AssetResponse(AssetBase):
    AssetID: int
    EmployeeID: Optional[str] = None
    EmployeeName: Optional[str] = None
    Department: Optional[str] = None
    Designation: Optional[str] = None
    Grade: Optional[str] = None
    DateIssued: Optional[date] = None

# --- Employee Schemas ---
class EmployeeBase(BaseModel):
    EmployeeID: str = Field(..., example="E101")
    EmployeeName: str = Field(..., example="John Doe")
    Department: Optional[str] = Field(None, example="IT")
    Designation: Optional[str] = Field(None, example="Systems Engineer")
    Grade: Optional[str] = Field(None, example="G8")

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeResponse(EmployeeBase):
    pass

# --- Asset Transfer Schemas ---
class TransferCreate(BaseModel):
    AssetID: int
    FromEmployeeID: Optional[str] = None
    ToEmployeeID: Optional[str] = None  # None if returned to IT stock
    HandledByID: str  # The IT personnel who handled the transfer
    TransferDate: Optional[date] = None
    Notes: Optional[str] = None
