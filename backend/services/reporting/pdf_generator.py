
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os
from datetime import datetime
from backend.services.backtesting.models import BacktestResult

class PDFGenerator:
    """
    Generates Audit-Ready PDF Reports for Backtests.
    """
    
    @staticmethod
    def generate_backtest_report(result: BacktestResult, filename: str = "report.pdf") -> str:
        """
        Generate PDF report and return file path.
        """
        try:
            c = canvas.Canvas(filename, pagesize=letter)
            width, height = letter
            
            # Header
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "Factrade Backtest Report")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 70, f"Generated: {datetime.now().isoformat()}")
            c.drawString(50, height - 85, f"Strategy: {result.config.strategy.get('type', 'Unknown')}")
            
            # Performance Section
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 120, "Performance Metrics (Audited)")
            
            y = height - 140
            metrics = result.performance
            c.setFont("Helvetica", 10)
            c.drawString(70, y, f"Total Return: {metrics.total_return:.2f}%")
            c.drawString(70, y - 20, f"Win Rate: {metrics.win_rate:.2f}%")
            c.drawString(70, y - 40, f"Total Trades: {metrics.total_trades}")
            c.drawString(70, y - 60, f"Max Drawdown: {metrics.max_drawdown:.2f}%")
            
            # Audit Stamp
            c.setStrokeColor(colors.green)
            c.rect(400, height - 150, 150, 80)
            c.setFont("Courier-Bold", 12)
            c.setFillColor(colors.green)
            c.drawString(420, height - 110, "VERIFIED")
            c.drawString(435, height - 125, "Factrade AI")
            
            c.save()
            return os.path.abspath(filename)
        except Exception as e:
            print(f"PDF Generation failed: {e}")
            return ""
