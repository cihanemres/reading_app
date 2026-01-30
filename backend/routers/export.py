from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models.user import User, UserRole
from models.reading_activity import PreReading, Practice, Answer
from models.evaluation import TeacherEvaluation
from models.story import Story
from auth.dependencies import get_current_user, require_role
from io import BytesIO
from datetime import datetime
import pandas as pd

# PDF imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

router = APIRouter(prefix="/api/export", tags=["Data Export"])

@router.get("/student/{student_id}/progress")
async def export_student_progress(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export individual student progress as Excel file
    """
    # Verify student exists
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Authorization check
    if current_user.rol not in [UserRole.TEACHER, UserRole.ADMIN]:
        if current_user.rol == UserRole.PARENT:
            # Parent can only export their own children
            if student.parent_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to export this student's data"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to export data"
            )
    
    # Fetch student data
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == student_id
    ).all()
    
    # Prepare data for Excel
    data = []
    for pr in pre_readings:
        story = db.query(Story).filter(Story.id == pr.story_id).first()
        
        # Get practice count
        practice_count = db.query(Practice).filter(
            Practice.ogrenci_id == student_id,
            Practice.story_id == pr.story_id
        ).count()
        
        # Get best practice speed
        best_practice = db.query(func.max(Practice.okuma_hizi)).filter(
            Practice.ogrenci_id == student_id,
            Practice.story_id == pr.story_id
        ).scalar()
        
        # Get quiz result
        answer = db.query(Answer).filter(
            Answer.ogrenci_id == student_id,
            Answer.story_id == pr.story_id
        ).first()
        
        # Get evaluation
        evaluation = db.query(TeacherEvaluation).filter(
            TeacherEvaluation.ogrenci_id == student_id,
            TeacherEvaluation.story_id == pr.story_id
        ).first()
        
        data.append({
            'Tarih': pr.created_at.strftime('%Y-%m-%d') if pr.created_at else '',
            'Hikaye': story.baslik if story else '',
            'İlk Okuma Hızı (kelime/dk)': round(pr.okuma_hizi, 1) if pr.okuma_hizi else 0,
            'En İyi Hız (kelime/dk)': round(best_practice, 1) if best_practice else 0,
            'Pratik Sayısı': practice_count,
            'Quiz Puanı': f"{answer.dogru_sayisi}/5" if answer else '',
            'Akıcılık Puanı': evaluation.akicilik_puan if evaluation else '',
            'Öğretmen Yorumu': evaluation.ogretmen_yorumu if evaluation else ''
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Calculate summary statistics
    summary_data = {
        'Metrik': [
            'Toplam Hikaye',
            'Ortalama İlk Okuma Hızı',
            'Ortalama En İyi Hız',
            'Toplam Pratik',
            'Ortalama Quiz Başarısı'
        ],
        'Değer': [
            len(pre_readings),
            f"{df['İlk Okuma Hızı (kelime/dk)'].mean():.1f} kelime/dk" if len(df) > 0 else '0',
            f"{df['En İyi Hız (kelime/dk)'].mean():.1f} kelime/dk" if len(df) > 0 else '0',
            df['Pratik Sayısı'].sum() if len(df) > 0 else 0,
            f"{(df['Quiz Puanı'].str.split('/').str[0].astype(float).mean() / 5 * 100):.1f}%" if len(df) > 0 and df['Quiz Puanı'].notna().any() else '0%'
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    
    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='Özet', index=False)
        df.to_excel(writer, sheet_name='Detaylı Okuma Geçmişi', index=False)
        
        # Auto-adjust column widths
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Generate filename
    filename = f"ogrenci_{student.ad_soyad.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@router.get("/class/{grade}/progress")
async def export_class_progress(
    grade: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db)
):
    """
    Export class-wide progress as Excel file
    """
    # Get all students in grade
    students = db.query(User).filter(
        User.rol == UserRole.STUDENT,
        User.sinif_duzeyi == grade
    ).all()
    
    if not students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No students found in grade {grade}"
        )
    
    # Prepare data
    data = []
    for student in students:
        # Count completed stories
        story_count = db.query(PreReading).filter(
            PreReading.ogrenci_id == student.id
        ).count()
        
        # Calculate average speed
        avg_speed = db.query(func.avg(PreReading.okuma_hizi)).filter(
            PreReading.ogrenci_id == student.id
        ).scalar()
        
        # Count practices
        practice_count = db.query(Practice).filter(
            Practice.ogrenci_id == student.id
        ).count()
        
        # Calculate quiz average
        answers = db.query(Answer).filter(
            Answer.ogrenci_id == student.id
        ).all()
        
        quiz_avg = sum(a.dogru_sayisi for a in answers) / len(answers) if answers else 0
        
        data.append({
            'Öğrenci Adı': student.ad_soyad,
            'Email': student.email,
            'Tamamlanan Hikaye': story_count,
            'Ortalama Hız (kelime/dk)': round(avg_speed, 1) if avg_speed else 0,
            'Toplam Pratik': practice_count,
            'Quiz Ortalaması': f"{quiz_avg:.1f}/5"
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Sort by completed stories
    df = df.sort_values('Tamamlanan Hikaye', ascending=False)
    
    # Create Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=f'{grade}. Sınıf', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets[f'{grade}. Sınıf']
        for column in worksheet.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
    
    output.seek(0)
    
    filename = f"{grade}_sinif_raporu_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@router.get("/class")
async def export_teacher_students(
    grade: int = None,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db)
):
    """
    Export teacher's own students as Excel file
    Optionally filter by grade
    Falls back to all students if no linked students
    """
    # First try to get teacher's linked students
    query = db.query(User).filter(
        User.rol == UserRole.STUDENT,
        User.teacher_id == current_user.id
    )
    
    if grade:
        query = query.filter(User.sinif_duzeyi == grade)
    
    students = query.all()
    
    # Fallback: if no linked students, get all students (for demo purposes)
    if not students:
        fallback_query = db.query(User).filter(User.rol == UserRole.STUDENT)
        if grade:
            fallback_query = fallback_query.filter(User.sinif_duzeyi == grade)
        students = fallback_query.all()
        
    if not students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sistemde öğrenci bulunamadı."
        )
    
    # Prepare data
    data = []
    for student in students:
        # Count completed stories
        story_count = db.query(PreReading).filter(
            PreReading.ogrenci_id == student.id
        ).count()
        
        # Calculate average speed
        avg_speed = db.query(func.avg(PreReading.okuma_hizi)).filter(
            PreReading.ogrenci_id == student.id
        ).scalar()
        
        # Count practices
        practice_count = db.query(Practice).filter(
            Practice.ogrenci_id == student.id
        ).count()
        
        # Calculate quiz average
        answers = db.query(Answer).filter(
            Answer.ogrenci_id == student.id
        ).all()
        
        quiz_avg = sum((a.dogru_sayisi or 0) for a in answers) / len(answers) if answers else 0
        
        data.append({
            'Öğrenci Adı': student.ad_soyad,
            'Email': student.email,
            'Sınıf': student.sinif_duzeyi,
            'Tamamlanan Hikaye': story_count,
            'Ortalama Hız (kelime/dk)': round(avg_speed, 1) if avg_speed else 0,
            'Toplam Pratik': practice_count,
            'Quiz Ortalaması': f"{quiz_avg:.1f}/5"
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Sort by name
    df = df.sort_values('Öğrenci Adı')
    
    # Create Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Öğrencilerim', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Öğrencilerim']
        for column in worksheet.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
    
    output.seek(0)
    
    filename = f"ogrencilerim_raporu_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# ==================== PDF EXPORT ENDPOINTS ====================

@router.get("/student/{student_id}/progress/pdf")
async def export_student_progress_pdf(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export individual student progress as PDF file
    """
    if not PDF_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF export not available. Install reportlab: pip install reportlab"
        )
    
    # Verify student exists
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Authorization check
    if current_user.rol not in [UserRole.TEACHER, UserRole.ADMIN]:
        if current_user.rol == UserRole.PARENT:
            if student.parent_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to export this student's data"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to export data"
            )
    
    # Fetch data
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == student_id
    ).order_by(PreReading.created_at.desc()).all()
    
    # Create PDF
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=1  # Center
    )
    elements.append(Paragraph(f"Öğrenci İlerleme Raporu", title_style))
    elements.append(Paragraph(f"<b>{student.ad_soyad}</b> - {student.sinif_duzeyi}. Sınıf", styles['Normal']))
    elements.append(Paragraph(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Summary Statistics
    total_stories = len(pre_readings)
    total_practices = db.query(Practice).filter(Practice.ogrenci_id == student_id).count()
    avg_speed = db.query(func.avg(PreReading.okuma_hizi)).filter(
        PreReading.ogrenci_id == student_id
    ).scalar() or 0
    
    elements.append(Paragraph("<b>Özet İstatistikler</b>", styles['Heading2']))
    summary_data = [
        ['Metrik', 'Değer'],
        ['Toplam Okunan Hikaye', str(total_stories)],
        ['Toplam Pratik Sayısı', str(total_practices)],
        ['Ortalama Okuma Hızı', f"{avg_speed:.1f} kelime/dk"],
    ]
    
    summary_table = Table(summary_data, colWidths=[200, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Reading History
    if pre_readings:
        elements.append(Paragraph("<b>Okuma Geçmişi</b>", styles['Heading2']))
        
        history_data = [['Tarih', 'Hikaye', 'Hız (k/dk)', 'Pratik']]
        for pr in pre_readings[:10]:  # Last 10 readings
            story = db.query(Story).filter(Story.id == pr.story_id).first()
            practice_count = db.query(Practice).filter(
                Practice.ogrenci_id == student_id,
                Practice.story_id == pr.story_id
            ).count()
            
            history_data.append([
                pr.created_at.strftime('%d.%m.%Y') if pr.created_at else '-',
                (story.baslik[:25] + '...') if story and len(story.baslik) > 25 else (story.baslik if story else '-'),
                f"{pr.okuma_hizi:.0f}" if pr.okuma_hizi else '-',
                str(practice_count)
            ])
        
        history_table = Table(history_data, colWidths=[80, 200, 80, 60])
        history_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(history_table)
    
    # Build PDF
    doc.build(elements)
    output.seek(0)
    
    filename = f"ogrenci_{student.ad_soyad.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        output,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@router.get("/class/{grade}/progress/pdf")
async def export_class_progress_pdf(
    grade: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db)
):
    """
    Export class-wide progress as PDF file
    """
    if not PDF_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF export not available. Install reportlab: pip install reportlab"
        )
    
    # Get all students in grade
    students = db.query(User).filter(
        User.rol == UserRole.STUDENT,
        User.sinif_duzeyi == grade
    ).order_by(User.ad_soyad).all()
    
    if not students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No students found in grade {grade}"
        )
    
    # Create PDF
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=1
    )
    elements.append(Paragraph(f"{grade}. Sınıf İlerleme Raporu", title_style))
    elements.append(Paragraph(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y')}", styles['Normal']))
    elements.append(Paragraph(f"Toplam Öğrenci: {len(students)}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Class Statistics
    total_stories = db.query(func.count(PreReading.id)).join(User).filter(
        User.sinif_duzeyi == grade
    ).scalar() or 0
    
    avg_class_speed = db.query(func.avg(PreReading.okuma_hizi)).join(User).filter(
        User.sinif_duzeyi == grade
    ).scalar() or 0
    
    elements.append(Paragraph("<b>Sınıf Özeti</b>", styles['Heading2']))
    class_summary = [
        ['Metrik', 'Değer'],
        ['Toplam Öğrenci', str(len(students))],
        ['Toplam Okuma Aktivitesi', str(total_stories)],
        ['Ortalama Sınıf Hızı', f"{avg_class_speed:.1f} kelime/dk"],
    ]
    
    summary_table = Table(class_summary, colWidths=[200, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Student List
    elements.append(Paragraph("<b>Öğrenci Listesi</b>", styles['Heading2']))
    
    student_data = [['#', 'Öğrenci', 'Hikaye', 'Hız', 'Pratik']]
    for idx, student in enumerate(students, 1):
        story_count = db.query(PreReading).filter(
            PreReading.ogrenci_id == student.id
        ).count()
        
        avg_speed = db.query(func.avg(PreReading.okuma_hizi)).filter(
            PreReading.ogrenci_id == student.id
        ).scalar()
        
        practice_count = db.query(Practice).filter(
            Practice.ogrenci_id == student.id
        ).count()
        
        student_data.append([
            str(idx),
            student.ad_soyad[:20],
            str(story_count),
            f"{avg_speed:.0f}" if avg_speed else '0',
            str(practice_count)
        ])
    
    student_table = Table(student_data, colWidths=[30, 180, 60, 60, 60])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(student_table)
    
    # Build PDF
    doc.build(elements)
    output.seek(0)
    
    filename = f"{grade}_sinif_raporu_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        output,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

