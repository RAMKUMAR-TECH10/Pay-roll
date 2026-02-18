
1. Project Identity & Architecture
System Type: Modular Manufacturing ERP (Enterprise Resource Planning).

Design Pattern: Flask Application Factory Pattern with Blueprints.

Structural Model: Modular separation (Core, Modules, Templates, Instance).

Logic Model: Relational Inventory Deduction (Stock linked to Production via Recipes).

2. Technology Stack (The "Things Used")
Core Language: Python 3.13.

Web Framework: Flask 3.1.2.

Database ORM: Flask-SQLAlchemy 3.1.1 (utilizing SQLAlchemy 2.0.46).

Authentication: Flask-Login 0.6.3.

Environment Management: Master Virtual Environment (master_venv) located on X: drive.

External Libraries:

ReportLab: For dynamic PDF report generation.

Werkzeug: For secure Bcrypt-style password hashing.

Python-Dotenv: For environment variable management.

3. Core Functional Modules
Inventory Logic: Implements automated stock deduction based on pre-defined recipes (e.g., 0.5kg wood/bundle).

Audit Trail: Tracks every material change via MaterialTransaction with before/after quantity logging.

Payroll Engine: Calculates wages based on real-time production counts multiplied by worker rates.

Background Monitoring: A threading module in app.py checks stock every 6 hours and triggers email alerts.

Export Service: Allows admins to generate CSV/PDF summaries for tax and business audits.

4. Industrial Applications
Primary Application: Matchbox manufacturing units requiring tight chemical and wood inventory control.

Scalable Applications:

Textile industries (Piece-rate worker tracking).

Food processing (Recipe-based ingredient deduction).

Packaging units (Unit-based material management).

5. Pros (Advantages)
Eliminates "Ghost Production": Every payroll entry must correspond to an inventory deduction.

DevOps Portability: The universal.bat launcher ensures the app runs on any Nitro laptop without "Environment Hell".

Data Integrity: Uses SQLite with foreign key constraints and CheckConstraints for non-negative stock.

Theft Prevention: The audit trail makes it impossible to change stock levels without an admin record.

6. Cons (Limitations)
Hardware Dependency: Currently optimized for local drive access (X: drive) rather than cloud-native databases.

Single-Threaded Database: SQLite is highly portable but can experience locking if hundreds of users access it at once.

Manual Recipe Updates: Changing a production recipe requires administrative input in the Recipe table.
