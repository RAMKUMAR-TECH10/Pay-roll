# Quick Start Guide

## Get Started in 3 Minutes!

### Step 1: Install Dependencies
```bash
cd "c:\Mini project\Payroll"
pip install -r requirements.txt
```

### Step 2: Run the Application
```bash
python app.py
```

### Step 3: Open in Browser
Navigate to: **http://localhost:5000**

That's it! The application will automatically:
- Create the database
- Seed initial materials
- Configure the production recipe

## First Time Usage

### 1. Check Dashboard
- View current inventory levels
- See production statistics

### 2. Log Production
- Go to **Production** page
- Enter number of bundles (e.g., 10)
- Add optional notes
- Click "Log Production"
- Materials are automatically deducted!

### 3. Restock Materials
- Go to **Inventory** page
- Select material to restock
- Enter quantity to add
- Add optional notes (supplier info)
- Click "Add Stock"

### 4. View Reports
- Go to **Reports** page
- Select date range (optional)
- View production summary
- See material consumption breakdown

## Key Features to Try

### ✨ Undo Production
If you made a mistake:
1. Go to Production page
2. Find the production log
3. Click **"Undo"** button
4. Materials are restored automatically!

### 📊 Check Stock Status
Materials are color-coded:
- 🔴 **Red**: Low stock (< 20 units) - Restock soon!
- 🟡 **Yellow**: Medium stock (20-50 units)
- 🟢 **Green**: Good stock (> 50 units)

### 📈 Production Analytics
- Weekly production trend chart on dashboard
- Detailed reports with date filtering
- Cost tracking per production run

### 🔌 API Access
Try the API endpoints:
```bash
# Get all materials (JSON)
http://localhost:5000/api/materials

# Get stockout prediction
http://localhost:5000/api/materials/1/stockout-prediction

# Get production cost
http://localhost:5000/api/production/1/cost
```

## Default Materials & Recipe

### Initial Inventory:
- Wood Splints: 500 kg @ ₹10/kg
- Chemical Paste: 100 kg @ ₹50/kg
- Cardboard Sheets: 1000 pcs @ ₹2/pc
- Glue: 50 liters @ ₹15/liter

### Recipe per Bundle:
- Wood Splints: 0.5 kg
- Chemical Paste: 0.1 kg
- Cardboard Sheets: 5 pcs
- Glue: 0.05 liters

**Example**: Producing 10 bundles will consume:
- 5 kg Wood Splints
- 1 kg Chemical Paste
- 50 Cardboard Sheets
- 0.5 liters Glue

## Troubleshooting

### Port Already in Use?
Change the port in `app.py`:
```python
app.run(debug=True, port=5001)
```

### Database Issues?
Delete and recreate:
```bash
del instance\payroll_new.db
python app.py
```

### Import Errors?
Reinstall dependencies:
```bash
pip install -r requirements.txt
```

## Need Help?

Check the full documentation in **README.md** for:
- Detailed feature explanations
- API documentation
- Database schema
- Advanced configuration

## What's New?

This optimized version includes:
- ✅ Undo production functionality
- ✅ Production notes
- ✅ Reports & analytics
- ✅ REST API endpoints
- ✅ Audit trail
- ✅ Pagination
- ✅ Cost tracking
- ✅ Stockout predictions
- ✅ Better error handling
- ✅ Modular code structure

Enjoy your optimized Matchbox Production Management System! 🎉
