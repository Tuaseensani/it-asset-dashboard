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

CREATE TABLE Users (
    UserID      INT IDENTITY(1,1) PRIMARY KEY,
    Username    VARCHAR(50) NOT NULL UNIQUE,   -- AD sAMAccountName
    DisplayName VARCHAR(100) NULL,
    Email       VARCHAR(150) NULL,
    ADGroups    VARCHAR(MAX) NULL,             -- comma-separated list from AD
    AppRole     VARCHAR(20) NOT NULL DEFAULT 'Viewer'
                CHECK (AppRole IN ('Admin','Manager','Viewer')),
    IsActive    BIT NOT NULL DEFAULT 1,
    LastLogin   DATETIME NULL,
    CreatedAt   DATETIME NOT NULL DEFAULT GETDATE()
);



UPDATE Users
SET AppRole = 'Admin'
WHERE Username = 'aamish.mirza';
select * from Users

SELECT UserID, Username, DisplayName, Email, AppRole, IsActive, LastLogin, CreatedAt
FROM Users;

USE ITAssets;
GO

ALTER TABLE Assets
ADD CreatedByUserID INT NULL REFERENCES Users(UserID);
GO

SELECT TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE COLUMN_NAME = 'CreatedByUserID'
  AND TABLE_NAME = 'Assets';
GO

SELECT a.AssetID, a.SerialNo, a.ItemType, a.CreatedByUserID, u.Username, u.DisplayName
FROM Assets a
LEFT JOIN Users u ON u.UserID = a.CreatedByUserID
WHERE a.SerialNo = 'TEST-AUDIT-001';

USE ITAssets;
GO

DELETE FROM Assets WHERE SerialNo = 'TEST-AUDIT-001';
GO

SELECT COUNT(*) AS RemainingTestAssets FROM Assets WHERE SerialNo LIKE 'TEST-%';
GO