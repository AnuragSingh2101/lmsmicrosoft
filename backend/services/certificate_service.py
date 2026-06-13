import os
import io
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import qrcode

def generate_certificate_pdf(student_name, course_name, issue_date=None, certificate_id=None, output_dir=None):
    """
    Generates a professional completion certificate PDF and saves it to output_dir.
    Returns (certificate_id, file_relative_path).
    """
    if not certificate_id:
        certificate_id = f"CERT-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[8:12].upper()}"
        
    if not issue_date:
        issue_date = datetime.utcnow()
        
    date_str = issue_date.strftime("%B %d, %Y")
    
    # Set up directory paths
    if not output_dir:
        # Default to a certificates subfolder inside the backend/uploads/ directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "uploads", "certificates")
        
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{certificate_id}.pdf"
    file_path = os.path.join(output_dir, filename)
    relative_path = f"uploads/certificates/{filename}"
    
    # Setup landscape layout
    width, height = landscape(letter)  # 792 x 612
    c = canvas.Canvas(file_path, pagesize=landscape(letter))
    
    # 1. Main outer border (Navy Blue / Slate)
    c.setStrokeColor(colors.HexColor("#1E3A8A"))  # Dark Blue
    c.setLineWidth(8)
    c.rect(25, 25, width - 50, height - 50)
    
    # 2. Inner thin border (Golden)
    c.setStrokeColor(colors.HexColor("#D97706"))  # Golden Amber
    c.setLineWidth(2)
    c.rect(33, 33, width - 66, height - 66)
    
    # 3. Corner decorative triangles
    def draw_corner_triangles():
        c.setFillColor(colors.HexColor("#1E3A8A"))
        # Top Left
        p1 = c.beginPath()
        p1.moveTo(25, height-25)
        p1.lineTo(65, height-25)
        p1.lineTo(25, height-65)
        c.drawPath(p1, fill=1, stroke=0)
        
        # Top Right
        p2 = c.beginPath()
        p2.moveTo(width-25, height-25)
        p2.lineTo(width-65, height-25)
        p2.lineTo(width-25, height-65)
        c.drawPath(p2, fill=1, stroke=0)
        
        # Bottom Left
        p3 = c.beginPath()
        p3.moveTo(25, 25)
        p3.lineTo(65, 25)
        p3.lineTo(25, 65)
        c.drawPath(p3, fill=1, stroke=0)
        
        # Bottom Right
        p4 = c.beginPath()
        p4.moveTo(width-25, 25)
        p4.lineTo(width-65, 25)
        p4.lineTo(width-25, 65)
        c.drawPath(p4, fill=1, stroke=0)
        
    draw_corner_triangles()
    
    # 4. Header Seal / Emblem placeholder text
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#D97706"))
    c.drawCentredString(width/2.0, 520, "MICROSOFT AGENTS LEAGUE HACKATHON")
    
    # 5. Main Heading
    c.setFont("Helvetica-Bold", 34)
    c.setFillColor(colors.HexColor("#1F2937"))  # Dark Slate
    c.drawCentredString(width/2.0, 460, "CERTIFICATE OF COMPLETION")
    
    # 6. Secondary text
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawCentredString(width/2.0, 415, "This is proudly presented to")
    
    # 7. Student Name
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(colors.HexColor("#1E3A8A"))  # Dark Blue
    c.drawCentredString(width/2.0, 360, student_name.upper())
    
    # 8. Achievement details
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawCentredString(width/2.0, 310, "for outstanding performance and successful completion of the curriculum for")
    
    # 9. Course Name
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#10B981"))  # Emerald Green
    c.drawCentredString(width/2.0, 265, course_name)
    
    # 10. Date of issue
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawCentredString(width/2.0, 220, f"Issued on: {date_str}")
    
    # 11. Certificate ID (printed in Courier monospace)
    c.setFont("Courier-Bold", 10)
    c.setFillColor(colors.HexColor("#9CA3AF"))
    c.drawCentredString(width/2.0, 190, f"Verification Code: {certificate_id}")
    
    # 12. Left signature lines
    c.setStrokeColor(colors.HexColor("#D1D5DB"))
    c.setLineWidth(1)
    c.line(80, 95, 230, 95)
    
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawString(90, 80, "Microsoft Agents League")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(90, 68, "Hackathon Creative Track Committee")
    
    # 13. Right signature lines
    c.line(width - 230, 95, width - 80, 95)
    
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawString(width - 210, 80, "AI LMS Coordinator")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(width - 210, 68, "System Generated Verification")
    
    # 14. Center QR Code (Verify URL)
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=3, border=1)
    # We point to localhost/verify endpoint
    verify_url = f"http://127.0.0.1:5000/verify/certificate/{certificate_id}"
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_io = io.BytesIO()
    try:
        qr_img.save(qr_io, format="PNG")
    except TypeError:
        # Fallback for image factories (like PyPNGImage) that do not support the 'format' argument
        qr_img.save(qr_io)
    qr_io.seek(0)    
    # Draw QR code in bottom-center
    reader = ImageReader(qr_io)
    c.drawImage(reader, width/2.0 - 35, 60, width=70, height=70)
    
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#9CA3AF"))
    c.drawCentredString(width/2.0, 48, "SCAN TO VERIFY")
    
    c.showPage()
    c.save()
    
    return certificate_id, relative_path
