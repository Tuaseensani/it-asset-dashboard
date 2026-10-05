CREATE DATABASE ITAssets;
GO
USE ITAssets;
GO

CREATE TABLE Employees (
    EmployeeID   VARCHAR(20) PRIMARY KEY,
    EmployeeName VARCHAR(100) NOT NULL,
    Department   VARCHAR(100),
    Designation  VARCHAR(100),
    Grade        VARCHAR(20)
);

CREATE TABLE Assets (
    AssetID     INT IDENTITY(1,1) PRIMARY KEY,
    ItemType    VARCHAR(50) NOT NULL,
    Brand       VARCHAR(50),
    Model       VARCHAR(100),
    SerialNo    VARCHAR(100) NOT NULL UNIQUE,
    Memory      VARCHAR(20),
    Storage     VARCHAR(20),
    Processor   VARCHAR(100),
    [Condition] VARCHAR(20) CHECK ([Condition] IN ('New','Good','Fair','Poor')),
    Status      VARCHAR(20) CHECK (Status IN ('Issued','In Stock','Under Repair','Retired'))
);

CREATE TABLE AssetTransfers (
    TransferID     INT IDENTITY(1,1) PRIMARY KEY,
    AssetID        INT NOT NULL REFERENCES Assets(AssetID),
    FromEmployeeID VARCHAR(20) NULL REFERENCES Employees(EmployeeID),
    ToEmployeeID   VARCHAR(20) NULL REFERENCES Employees(EmployeeID),
    HandledByID    VARCHAR(20) NOT NULL REFERENCES Employees(EmployeeID),
    TransferDate   DATE NOT NULL DEFAULT GETDATE(),
    Notes          VARCHAR(500) NULL
);
