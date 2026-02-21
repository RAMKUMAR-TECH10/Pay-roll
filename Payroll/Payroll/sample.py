import datetime

# --- MODULE 1: RAW MATERIAL (Database) ---
# Format: "Material_Name": [Current_Quantity, Unit, Unit_Price]
raw_materials = {
    "Wood Splints": [500.0, "kg", 10],
    "Chemical Paste": [100.0, "kg", 50],
    "Cardboard Sheets": [1000.0, "pcs", 2],
    "Glue": [50.0, "liters", 15]
}

# --- MODULE 2: PRODUCTION LOGIC ---
# Standard "Recipe" for 1 Bundle (10 matchboxes)
# This is our Bill of Materials (BOM)
RECIPE = {
    "Wood Splints": 0.25,      # 0.25 kg per bundle
    "Chemical Paste": 0.7,     # 0.7 kg per bundle
    "Cardboard Sheets": 0.12,  # 0.12 kg per bundle
    "Glue": 0.0               # 0.0 kg per bundle
}

production_history = []

def run_production():
    print("\n--- Start New Production Run ---")
    try:
        quantity = int(input("How many bundles are you producing today? "))
    except ValueError:
        print("Invalid input. Please enter a number.")
        return

    # Check if we have enough materials first
    can_produce = True
    for material, amt_needed in RECIPE.items():
        total_needed = amt_needed * quantity
        if raw_materials[material][0] < total_needed:
            print(f"❌ ERROR: Not enough {material}. Need {total_needed}, but only have {raw_materials[material][0]}")
            can_produce = False
    
    # If materials are available, proceed
    if can_produce:
        print("✅ Materials verified. Processing...")
        for material, amt_needed in RECIPE.items():
            # DEDUCT from Raw Material Module
            raw_materials[material][0] -= (amt_needed * quantity)
        
        # Log to Production Module
        entry = {
            "date": datetime.date.today(),
            "quantity": quantity,
            "status": "Completed"
        }
        production_history.append(entry)
        print(f"🎉 Production of {quantity} bundles finished successfully!")

def view_stock():
    print("\n--- Current Raw Material Stock ---")
    print(f"{'Material':<18} | {'Stock':<10} | {'Unit'}")
    print("-" * 40)
    for mat, details in raw_materials.items():
        print(f"{mat:<18} | {details[0]:<10.2f} | {details[1]}")

# --- SIMPLE USER INTERFACE ---
while True:
    print("\nMATCHBOX INDUSTRY MANAGEMENT SYSTEM")
    print("1. View Raw Material Stock")
    print("2. Run Production")
    print("3. View Production History")
    print("4. Exit")
    
    choice = input("Select an option: ")
    
    if choice == "1":
        view_stock()
    elif choice == "2":
        run_production()
    elif choice == "3":
        print("\n--- Production History ---")
        for log in production_history:
            print(f"Date: {log['date']} | Bundles: {log['quantity']} | Status: {log['status']}")
    elif choice == "4":
        print("Exiting system. Goodbye!")
        break
    else:
        print("Invalid choice, try again.")