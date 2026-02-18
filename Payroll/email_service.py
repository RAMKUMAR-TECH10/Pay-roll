import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from models import RawMaterial
from services import InventoryService, ReportService
import datetime

class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.smtp_server = app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = app.config.get('SMTP_PORT', 587)
        self.smtp_username = app.config.get('SMTP_USERNAME', '')
        self.smtp_password = app.config.get('SMTP_PASSWORD', '')
        self.sender_email = app.config.get('SENDER_EMAIL', self.smtp_username)
        self.enabled = app.config.get('EMAIL_ENABLED', False)
    
    def send_email(self, to_email, subject, body_html, body_text=None, attachments=None):
        """Send an email"""
        if not self.enabled:
            print(f"Email disabled. Would send to {to_email}: {subject}")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text and HTML parts
            if body_text:
                msg.attach(MIMEText(body_text, 'plain'))
            msg.attach(MIMEText(body_html, 'html'))
            
            # Add attachments
            if attachments:
                for filename, content in attachments.items():
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename={filename}')
                    msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_low_stock_alert(self, to_email, low_stock_materials):
        """Send low stock alert email"""
        subject = "⚠️ Low Stock Alert - Matchbox Production System"
        
        # Create HTML body
        materials_html = ""
        for material in low_stock_materials:
            status_color = "#ef4444" if material.quantity < 10 else "#f59e0b"
            materials_html += f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;">{material.name}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{material.quantity:.2f} {material.unit}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">
                    <span style="background: {status_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                        LOW STOCK
                    </span>
                </td>
            </tr>
            """
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #ef4444;">⚠️ Low Stock Alert</h2>
                <p>The following materials are running low and need to be restocked:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <thead>
                        <tr style="background: #3b82f6; color: white;">
                            <th style="padding: 10px; text-align: left;">Material</th>
                            <th style="padding: 10px; text-align: right;">Current Stock</th>
                            <th style="padding: 10px; text-align: center;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {materials_html}
                    </tbody>
                </table>
                
                <p style="margin-top: 20px;">
                    <strong>Action Required:</strong> Please restock these materials to avoid production delays.
                </p>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    This is an automated notification from Matchbox Production Management System.
                </p>
            </div>
        </body>
        </html>
        """
        
        body_text = f"Low Stock Alert\n\n"
        for material in low_stock_materials:
            body_text += f"- {material.name}: {material.quantity:.2f} {material.unit}\n"
        
        return self.send_email(to_email, subject, body_html, body_text)
    
    def send_daily_summary(self, to_email):
        """Send daily production summary"""
        today = datetime.date.today()
        summary = ReportService.get_production_summary(today, today)
        
        subject = f"📊 Daily Production Summary - {today.strftime('%B %d, %Y')}"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #3b82f6;">📊 Daily Production Summary</h2>
                <p><strong>Date:</strong> {today.strftime('%B %d, %Y')}</p>
                
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Production Metrics</h3>
                    <table style="width: 100%;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Production Runs:</strong></td>
                            <td style="text-align: right;">{summary['total_production_runs']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Total Bundles:</strong></td>
                            <td style="text-align: right;">{summary['total_bundles']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Total Cost:</strong></td>
                            <td style="text-align: right;">₹{summary['total_cost']:.2f}</td>
                        </tr>
                    </table>
                </div>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    This is an automated daily summary from Matchbox Production Management System.
                </p>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""Daily Production Summary - {today.strftime('%B %d, %Y')}
        
Production Runs: {summary['total_production_runs']}
Total Bundles: {summary['total_bundles']}
Total Cost: ₹{summary['total_cost']:.2f}
"""
        
        return self.send_email(to_email, subject, body_html, body_text)
    
    def send_weekly_report(self, to_email):
        """Send weekly production report"""
        today = datetime.date.today()
        week_ago = today - datetime.timedelta(days=7)
        summary = ReportService.get_production_summary(week_ago, today)
        
        subject = f"📈 Weekly Production Report - Week of {week_ago.strftime('%B %d, %Y')}"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #3b82f6;">📈 Weekly Production Report</h2>
                <p><strong>Period:</strong> {week_ago.strftime('%B %d')} - {today.strftime('%B %d, %Y')}</p>
                
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Weekly Summary</h3>
                    <table style="width: 100%;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Production Runs:</strong></td>
                            <td style="text-align: right;">{summary['total_production_runs']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Total Bundles:</strong></td>
                            <td style="text-align: right;">{summary['total_bundles']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Total Cost:</strong></td>
                            <td style="text-align: right;">₹{summary['total_cost']:.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Average per Run:</strong></td>
                            <td style="text-align: right;">{summary['avg_bundles_per_run']:.2f} bundles</td>
                        </tr>
                    </table>
                </div>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    This is an automated weekly report from Matchbox Production Management System.
                </p>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""Weekly Production Report
Period: {week_ago.strftime('%B %d')} - {today.strftime('%B %d, %Y')}

Production Runs: {summary['total_production_runs']}
Total Bundles: {summary['total_bundles']}
Total Cost: ₹{summary['total_cost']:.2f}
Average per Run: {summary['avg_bundles_per_run']:.2f} bundles
"""
        
        return self.send_email(to_email, subject, body_html, body_text)
    
    def check_and_send_low_stock_alerts(self, recipients):
        """Check stock levels and send alerts if needed"""
        low_stock_materials = InventoryService.get_low_stock_materials(threshold=20)
        
        if low_stock_materials:
            for email in recipients:
                self.send_low_stock_alert(email, low_stock_materials)
            return True
        return False
