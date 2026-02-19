1. Project Identity & Architecture
System Type: Modular Manufacturing ERP (Enterprise Resource Planning).

Design Pattern: Flask Application Factory Pattern with Blueprints for scalable module management.

Structural Model: Strict modular separation (Core, Modules, Templates, Instance) to ensure code maintainability.

Logic Model: Relational Inventory Deduction—stock is mathematically linked to production output via configurable Recipes.

2. Technology Stack
Core Language: Python 3.13+.

Web Framework: Flask 3.1.2.

Database ORM: Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.0.46).

Authentication: Flask-Login 0.6.3 with session-based persistence.

Environment Management: Standardized via requirements.txt and .env files for cross-platform compatibility.

Libraries: ReportLab (PDFs), Werkzeug (Security), Python-Dotenv (Config).

3. Core Functional Modules
Automated Inventory: Real-time stock deduction triggered by production entries.

Transaction Audit: Comprehensive logging of all stock movements (restock, production, adjustments).

Payroll Engine: Dynamic wage calculation based on production logs and worker-specific rates.

Background Services: Multi-threaded stock monitoring and automated email alert system.

4. Pros (Advantages)
High Portability: Path-independent design allows deployment on any OS (Windows/Linux/macOS).

Production Integrity: Ensures every payroll rupee spent is accounted for by a corresponding drop in raw material stock.

Data Security: Implements industry-standard password hashing and Role-Based Access Control (RBAC).

5. Cons (Limitations)
Database Concurrency: Uses SQLite; ideal for small-to-medium factories but limited for high-concurrency enterprise environments.

Manual Master Data: Initial recipe and material setup requires administrative configuration.
