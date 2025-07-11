"""
PDF Export utilities for meal planning
"""

import os
from io import BytesIO
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import calendar

class MealPlanPDFExporter:
    """Create beautiful PDF exports for meal plans"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom styles for the PDF"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#34495e'),
            fontName='Helvetica-Bold'
        )
        
        # Day header style
        self.day_style = ParagraphStyle(
            'DayHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#3498db'),
            fontName='Helvetica-Bold'
        )
        
        # Meal style
        self.meal_style = ParagraphStyle(
            'MealStyle',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            leftIndent=20,
            fontName='Helvetica'
        )
        
        # Note style
        self.note_style = ParagraphStyle(
            'NoteStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#7f8c8d'),
            fontName='Helvetica-Oblique'
        )

    def create_weekly_meal_plan_pdf(self, week_data, week_start, week_end, user):
        """Create a beautiful PDF for weekly meal plan"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Title
        title = f"Meal Plan: {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}"
        elements.append(Paragraph(title, self.title_style))
        
        # User info
        user_info = f"Prepared for: {user.get_full_name() or user.username}"
        elements.append(Paragraph(user_info, self.subtitle_style))
        
        # Generation date
        gen_date = f"Generated on: {datetime.now().strftime('%Y-%m-%d at %H:%M UTC')}"
        elements.append(Paragraph(gen_date, self.note_style))
        
        elements.append(Spacer(1, 20))
        
        # Week overview table
        self.add_week_overview_table(elements, week_data)
        
        elements.append(Spacer(1, 30))
        
        # Daily meal plans
        for day in week_data:
            self.add_daily_meal_plan(elements, day)
        
        # Footer with summary
        self.add_meal_summary(elements, week_data)
        
        # Build PDF
        doc.build(elements, onFirstPage=self.add_header_footer, onLaterPages=self.add_header_footer)
        
        # Get the value of the BytesIO buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        return pdf
    
    def add_week_overview_table(self, elements, week_data):
        """Add a beautiful overview table for the week"""
        elements.append(Paragraph("📅 Week Overview", self.subtitle_style))
        
        # Create table data
        table_data = [['Day', 'Breakfast', 'Lunch', 'Dinner', 'Snack']]
        
        for day in week_data:
            row = [
                Paragraph(f"<b>{day['day_name']}</b><br/>{day['date'].strftime('%m/%d')}", self.meal_style)
            ]
            
            for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
                meals = day['meals'].get(meal_type, [])
                if meals:
                    meal_text = '<br/>'.join([f"• {meal.recipe.title[:25]}{'...' if len(meal.recipe.title) > 25 else ''}" for meal in meals])
                    row.append(Paragraph(meal_text, self.meal_style))
                else:
                    row.append(Paragraph("—", self.note_style))
            
            table_data.append(row)
        
        # Create table
        table = Table(table_data, colWidths=[1.2*inch, 1.8*inch, 1.8*inch, 1.8*inch, 1.2*inch])
        
        # Style the table
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
    
    def add_daily_meal_plan(self, elements, day):
        """Add detailed daily meal plan"""
        # Day header
        day_title = f"{day['day_name']}, {day['date'].strftime('%B %d, %Y')}"
        if day.get('is_today'):
            day_title += " 🌟 (Today)"
        
        elements.append(Paragraph(day_title, self.day_style))
        
        # Meals for the day
        meal_icons = {
            'breakfast': '🥐',
            'lunch': '🥗', 
            'dinner': '🍽️',
            'snack': '🍎'
        }
        
        for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
            meals = day['meals'].get(meal_type, [])
            
            if meals:
                meal_header = f"{meal_icons.get(meal_type, '🍴')} {meal_type.title()}"
                elements.append(Paragraph(meal_header, self.subtitle_style))
                
                for meal in meals:
                    recipe_info = f"<b>{meal.recipe.title}</b>"
                    if meal.servings > 1:
                        recipe_info += f" <i>(serves {meal.servings})</i>"
                    
                    if meal.recipe.category:
                        recipe_info += f" - <font color='#7f8c8d'>{meal.recipe.category.name}</font>"
                    
                    if hasattr(meal.recipe, 'total_time') and meal.recipe.total_time:
                        recipe_info += f" - <font color='#e67e22'>{meal.recipe.total_time} min</font>"
                    
                    elements.append(Paragraph(recipe_info, self.meal_style))
                    
                    if meal.notes:
                        elements.append(Paragraph(f"Note: {meal.notes}", self.note_style))
        
        elements.append(Spacer(1, 15))
    
    def add_meal_summary(self, elements, week_data):
        """Add meal plan summary"""
        elements.append(Paragraph("📊 Week Summary", self.subtitle_style))
        
        # Count meals and recipes
        total_meals = 0
        unique_recipes = set()
        category_count = {}
        
        for day in week_data:
            for meal_type, meals in day['meals'].items():
                for meal in meals:
                    total_meals += 1
                    unique_recipes.add(meal.recipe.id)
                    
                    if meal.recipe.category:
                        category_name = meal.recipe.category.name
                        category_count[category_name] = category_count.get(category_name, 0) + 1
        
        # Summary text
        summary_text = f"""
        <b>Total Meals Planned:</b> {total_meals}<br/>
        <b>Unique Recipes:</b> {len(unique_recipes)}<br/>
        <b>Most Popular Category:</b> {max(category_count.items(), key=lambda x: x[1])[0] if category_count else 'None'}<br/>
        """
        
        elements.append(Paragraph(summary_text, self.meal_style))
        
        # Category breakdown
        if category_count:
            elements.append(Paragraph("Recipe Categories:", self.subtitle_style))
            for category, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
                elements.append(Paragraph(f"• {category}: {count} meal{'s' if count > 1 else ''}", self.meal_style))
    
    def add_header_footer(self, canvas, doc):
        """Add header and footer to each page"""
        canvas.saveState()
        
        # Header
        canvas.setFont('Helvetica-Bold', 16)
        canvas.setFillColor(colors.HexColor('#2c3e50'))
        canvas.drawString(72, A4[1] - 50, "🍽️ Recipe Manager")
        
        # Footer
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#7f8c8d'))
        canvas.drawRightString(A4[0] - 72, 30, f"Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M UTC')}")
        canvas.drawString(72, 30, f"Page {doc.page}")
        
        canvas.restoreState()

# Export function to be used in views
def export_week_to_pdf(week_data, week_start, week_end, user):
    """Export weekly meal plan to PDF"""
    exporter = MealPlanPDFExporter()
    pdf_content = exporter.create_weekly_meal_plan_pdf(week_data, week_start, week_end, user)
    
    # Create HTTP response
    response = HttpResponse(content_type='application/pdf')
    filename = f"meal_plan_{week_start.strftime('%Y%m%d')}_{week_end.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf_content)
    
    return response

