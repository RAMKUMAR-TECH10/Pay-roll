import csv
import io
from datetime import datetime
from flask import make_response
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from models import RawMaterial, ProductionLog, MaterialTransaction
from services import ReportService

class ExportService:
    """Service for exporting data to various formats"""
    
    @staticmethod
    def export_production_to_csv(start_date=None, end_date=None):
        """Export production logs to CSV"""
        query = ProductionLog.query.filter_by(is_deleted=False)
        
        if start_date:
            query = query.filter(ProductionLog.date >= start_date)
        if end_date:
            query = query.filter(ProductionLog.date <= end_date)
        
        logs = query.order_by(ProductionLog.date.desc()).all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'Bundles Produced', 'Notes', 'Created At'])
        
        # Write data
        for log in logs:
            writer.writerow([
                log.date.strftime('%Y-%m-%d'),
                log.bundles_produced,
                log.notes or '',
                log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else ''
            ])
        
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def export_inventory_to_csv():
        """Export current inventory to CSV"""
        materials = RawMaterial.query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Material', 'Quantity', 'Unit', 'Unit Price', 'Total Value', 'Status'])
        
        # Write data
        for material in materials:
            total_value = material.quantity * material.unit_price
            writer.writerow([
                material.name,
                f"{material.quantity:.2f}",
                material.unit,
                f"{material.unit_price:.2f}",
                f"{total_value:.2f}",
                material.stock_status
            ])
        
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def export_material_transactions_to_csv(material_id=None, start_date=None, end_date=None):
        """Export material transactions to CSV"""
        query = MaterialTransaction.query
        
        if material_id:
            query = query.filter_by(material_id=material_id)
        if start_date:
            query = query.filter(MaterialTransaction.created_at >= start_date)
        if end_date:
            query = query.filter(MaterialTransaction.created_at <= end_date)
        
        transactions = query.order_by(MaterialTransaction.created_at.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'Material', 'Type', 'Quantity Change', 'Before', 'After', 'Notes'])
        
        # Write data
        for trans in transactions:
            writer.writerow([
                trans.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                trans.material.name if trans.material else 'Unknown',
                trans.transaction_type,
                f"{trans.quantity_change:.2f}",
                f"{trans.quantity_before:.2f}",
                f"{trans.quantity_after:.2f}",
                trans.notes or ''
            ])
        
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def export_production_report_to_pdf(start_date=None, end_date=None):
        """Export production report to PDF"""
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        title = Paragraph("Production Report", title_style)
        elements.append(title)
        
        # Date range
        date_range = f"Period: {start_date.strftime('%Y-%m-%d') if start_date else 'All'} to {end_date.strftime('%Y-%m-%d') if end_date else 'All'}"
        date_para = Paragraph(date_range, styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 20))
        
        # Get summary data
        summary = ReportService.get_production_summary(start_date, end_date)
        
        # Summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Total Production Runs', str(summary['total_production_runs'])],
            ['Total Bundles Produced', str(summary['total_bundles'])],
            ['Total Cost', f"₹{summary['total_cost']:.2f}"],
            ['Average Bundles per Run', f"{summary['avg_bundles_per_run']:.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 30))
        
        # Production logs
        query = ProductionLog.query.filter_by(is_deleted=False)
        if start_date:
            query = query.filter(ProductionLog.date >= start_date)
        if end_date:
            query = query.filter(ProductionLog.date <= end_date)
        
        logs = query.order_by(ProductionLog.date.desc()).limit(50).all()
        
        if logs:
            elements.append(Paragraph("Recent Production Logs", styles['Heading2']))
            elements.append(Spacer(1, 12))
            
            log_data = [['Date', 'Bundles', 'Notes']]
            for log in logs:
                log_data.append([
                    log.date.strftime('%Y-%m-%d'),
                    str(log.bundles_produced),
                    (log.notes[:30] + '...') if log.notes and len(log.notes) > 30 else (log.notes or '-')
                ])
            
            log_table = Table(log_data, colWidths=[1.5*inch, 1*inch, 3.5*inch])
            log_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8)
            ]))
            
            elements.append(log_table)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def export_inventory_report_to_pdf():
        """Export inventory report to PDF"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=30,
            alignment=1
        )
        
        title = Paragraph("Inventory Report", title_style)
        elements.append(title)
        
        # Date
        date_para = Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 20))
        
        # Get materials
        materials = RawMaterial.query.all()
        
        # Inventory table
        inv_data = [['Material', 'Quantity', 'Unit', 'Unit Price', 'Total Value', 'Status']]
        total_value = 0
        
        for material in materials:
            value = material.quantity * material.unit_price
            total_value += value
            status = material.stock_status.upper()
            
            inv_data.append([
                material.name,
                f"{material.quantity:.2f}",
                material.unit,
                f"₹{material.unit_price:.2f}",
                f"₹{value:.2f}",
                status
            ])
        
        # Add total row
        inv_data.append(['', '', '', 'TOTAL:', f"₹{total_value:.2f}", ''])
        
        inv_table = Table(inv_data, colWidths=[1.8*inch, 1*inch, 0.8*inch, 1*inch, 1.2*inch, 0.8*inch])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9)
        ]))
        
        elements.append(inv_table)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
