# Matchbox Production Management System

A comprehensive Flask-based web application for managing matchbox production, raw material inventory, and production analytics.

## Features

### Core Functionality
- **Raw Material Management**: Track inventory levels with automatic deduction during production
- **Production Logging**: Record production runs with notes and automatic material consumption
- **Production Undo**: Reverse production logs and restore materials
- **Audit Trail**: Complete transaction history for all material movements
- **Reports & Analytics**: Production summaries and material consumption reports

### Technical Features
- **Modular Architecture**: Separated concerns (models, routes, services, config)
- **Service Layer**: Business logic abstraction for better maintainability
- **Database Transactions**: Atomic operations with rollback support
- **Soft Deletes**: Production logs can be deleted without losing history
- **Pagination**: Efficient handling of large datasets
- **REST API**: JSON endpoints for external integrations
- **Error Handling**: Custom 404/500 error pages
- **Configurable Recipe**: Database-driven production recipes

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone or download the project**
   ```bash
   cd "d:\New folder\Payroll"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables (optional)**
   ```bash
   copy .env.example .env
   # Edit .env file with your settings
   ```

    Run the application using the runner script:
    ```powershell
    ./run.ps1
    ```
    Alternatively, you can run it manually with the virtual environment:
    ```bash
    .venv\Scripts\python app.py
    ```

7. **Access the application**
   Open your browser and navigate to: `http://localhost:5000`

## Project Structure

```
Payroll/
├── app.py                  # Application factory and entry point
├── config.py              # Configuration settings
├── models.py              # Database models
├── routes.py              # Route handlers (Blueprint)
├── services.py            # Business logic layer
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── instance/             # Database files (auto-created)
│   └── payroll_new.db
├── static/
│   └── css/
│       └── style.css     # Stylesheets
└── templates/
    ├── base.html         # Base template
    ├── dashboard.html    # Dashboard page
    ├── production.html   # Production logging
    ├── inventory.html    # Inventory management
    ├── reports.html      # Reports & analytics
    └── errors/
        ├── 404.html      # Not found page
        └── 500.html      # Server error page
```

## Usage Guide

### Dashboard
- View production statistics for today
- See weekly production trends (chart)
- Monitor raw material stock levels
- Get low stock alerts

### Production Module
1. Enter the number of bundles produced
2. Optionally add notes (e.g., shift info, quality notes)
3. Click "Log Production"
4. Materials are automatically deducted based on the recipe
5. View production history with pagination
6. **Undo** production to restore materials
7. **Delete** production logs (soft delete)

### Inventory Module
1. Select material to restock
2. Enter quantity to add
3. Optionally add notes (supplier, invoice number)
4. Click "Add Stock"
5. View current stock levels with status indicators
   - **Red**: Low stock (< 20 units)
   - **Yellow**: Medium stock (20-50 units)
   - **Green**: Good stock (> 50 units)

### Reports Module
1. Select date range for analysis
2. View production summary:
   - Total production runs
   - Total bundles produced
   - Total cost
   - Average bundles per run
3. View material consumption breakdown
4. Export functionality (coming soon)

## API Endpoints

### Materials
- `GET /api/materials` - Get all materials
- `GET /api/materials/<id>` - Get specific material
- `GET /api/materials/<id>/stockout-prediction` - Predict stockout date

### Production
- `GET /api/production` - Get production logs
- `GET /api/production/<id>/cost` - Get production cost

## Database Schema

### RawMaterial
- `id`: Primary key
- `name`: Material name (unique)
- `quantity`: Current stock level
- `unit`: Unit of measurement
- `unit_price`: Price per unit
- `created_at`, `updated_at`: Timestamps

### ProductionLog
- `id`: Primary key
- `date`: Production date
- `bundles_produced`: Number of bundles
- `notes`: Optional notes
- `is_deleted`: Soft delete flag
- `created_at`: Timestamp

### MaterialTransaction
- `id`: Primary key
- `material_id`: Foreign key to RawMaterial
- `transaction_type`: 'restock', 'production', 'adjustment'
- `quantity_change`: Amount changed (+ or -)
- `quantity_before`, `quantity_after`: Stock levels
- `production_log_id`: Foreign key (if related to production)
- `notes`: Transaction notes
- `created_at`: Timestamp

### Recipe
- `id`: Primary key
- `material_id`: Foreign key to RawMaterial
- `quantity_per_bundle`: Amount needed per bundle
- `is_active`: Active status
- `created_at`, `updated_at`: Timestamps

## Configuration

### Environment Variables
Create a `.env` file based on `.env.example`:

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development  # or production
DATABASE_URL=sqlite:///payroll_new.db
```

### Config Classes
- `DevelopmentConfig`: Debug mode enabled
- `ProductionConfig`: Debug mode disabled
- `TestingConfig`: For unit tests

## Advanced Features

### Undo Production
The system tracks all material transactions. When you undo a production:
1. Materials are restored to inventory
2. Reversal transactions are created
3. Production log is soft-deleted
4. Complete audit trail is maintained

### Stockout Prediction
The API can predict when materials will run out based on:
- Last 30 days of consumption
- Current stock levels
- Average daily usage

### Cost Tracking
Each production run's cost is calculated based on:
- Materials consumed
- Unit prices at time of production
- Stored in transaction history

## Troubleshooting

### Database Issues
If you encounter database errors:
```bash
# Delete old database
del instance\payroll_new.db

# Restart application (will recreate DB)
python app.py
```

### Import Errors
Make sure virtual environment is activated:
```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### Port Already in Use
Change the port in `app.py`:
```python
app.run(debug=True, port=5001)
```

## Future Enhancements
- [ ] User authentication and authorization
- [ ] Export to CSV/PDF
- [ ] Email notifications for low stock
- [ ] Mobile-responsive design improvements
- [ ] Batch import from Excel
- [ ] Production scheduling
- [ ] Multi-user support with roles
- [ ] Advanced analytics dashboard

## License
This project is for educational purposes.

## Support
For issues or questions, please check the code comments or create an issue in the repository.
