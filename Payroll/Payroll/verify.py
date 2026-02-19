from app import app, db, Employee, RawMaterial, ProductionLog, Payroll, init_db
import os

# Reset DB for testing
if os.path.exists('payroll.db'):
    os.remove('payroll.db')

def run_test():
    with app.app_context():
        init_db()
        print("✅ Database Initialized")

        # 1. Create Employee
        emp = Employee(name="John Doe", role="Worker", rate_per_bundle=5.0)
        db.session.add(emp)
        db.session.commit()
        print(f"✅ Employee Created: {emp.name}")

        # 2. Add Stock (Restock)
        # Initial stock is seeded logs: Wood=500
        wood = RawMaterial.query.filter_by(name="Wood Splints").first()
        initial_wood = wood.quantity
        wood.quantity += 100
        db.session.commit()
        print(f"✅ Stock Added. Wood: {initial_wood} -> {wood.quantity}")

        # 3. Production Run (10 bundles)
        # Recipe for 10 bundles: Wood = 0.5 * 10 = 5kg
        qty = 10
        wood_needed = 0.5 * qty
        
        wood.quantity -= wood_needed
        log = ProductionLog(employee_id=emp.id, bundles_produced=qty)
        db.session.add(log)
        db.session.commit()
        
        expected_wood = initial_wood + 100 - wood_needed
        assert wood.quantity == expected_wood
        print(f"✅ Production Logged. Wood deducted correctly to {wood.quantity}")

        # 4. Payroll Generation
        unpaid = ProductionLog.query.filter_by(employee_id=emp.id, is_paid=False).all()
        assert len(unpaid) == 1
        
        total_bundles = sum(l.bundles_produced for l in unpaid)
        amount = total_bundles * emp.rate_per_bundle # 10 * 5 = 50
        
        payroll = Payroll(
            employee_id=emp.id,
            start_date=unpaid[0].date,
            end_date=unpaid[0].date,
            total_bundles=total_bundles,
            total_amount=amount,
            status="Paid"
        )
        for l in unpaid:
            l.is_paid = True
        
        db.session.add(payroll)
        db.session.commit()
        print(f"✅ Payroll Generated: ₹{amount}")

        # 5. Verify marked as paid
        unpaid_again = ProductionLog.query.filter_by(employee_id=emp.id, is_paid=False).all()
        assert len(unpaid_again) == 0
        print("✅ Logs marked as paid.")

if __name__ == "__main__":
    try:
        run_test()
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise e
