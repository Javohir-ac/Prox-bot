"""
Excel statistika generator
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
import os

def generate_statistics_excel(stats, filename='statistics.xlsx'):
    """Statistikani Excel formatda yaratish"""
    
    # Yangi workbook yaratish
    wb = Workbook()
    
    # Professional ko'k-kulrang dizayn
    # To'q ko'k - headerlar uchun
    dark_blue_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    dark_blue_font = Font(bold=True, color="FFFFFF", size=13, name='Calibri')
    
    # Och ko'k - bo'limlar uchun
    light_blue_fill = PatternFill(start_color="D6EAF8", end_color="D6EAF8", fill_type="solid")
    light_blue_font = Font(bold=True, color="1F4E78", size=11, name='Calibri')
    
    # Och kulrang - alternativ qatorlar
    light_gray_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    
    # Oq - asosiy qatorlar
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    # Yashil - faol userlar
    green_fill = PatternFill(start_color="D5F4E6", end_color="D5F4E6", fill_type="solid")
    
    # Sariq - o'rtacha faol
    yellow_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    
    # Border style
    medium_border = Border(
        left=Side(style='medium', color='1F4E78'),
        right=Side(style='medium', color='1F4E78'),
        top=Side(style='medium', color='1F4E78'),
        bottom=Side(style='medium', color='1F4E78')
    )
    
    thin_border = Border(
        left=Side(style='thin', color='BDC3C7'),
        right=Side(style='thin', color='BDC3C7'),
        top=Side(style='thin', color='BDC3C7'),
        bottom=Side(style='thin', color='BDC3C7')
    )
    
    # 1. UMUMIY STATISTIKA SHEET
    ws_summary = wb.active
    ws_summary.title = "Umumiy Statistika"
    
    # Title qatori - to'q ko'k
    ws_summary['A1'] = 'BOT STATISTIKASI'
    ws_summary['A1'].font = Font(bold=True, size=18, color="FFFFFF", name='Calibri')
    ws_summary['A1'].fill = dark_blue_fill
    ws_summary['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws_summary['A1'].border = medium_border
    ws_summary.merge_cells('A1:B1')
    ws_summary.row_dimensions[1].height = 35
    
    # Header qatori - och ko'k
    ws_summary['A2'] = 'Ko\'rsatkich'
    ws_summary['B2'] = 'Qiymat'
    ws_summary['A2'].fill = light_blue_fill
    ws_summary['B2'].fill = light_blue_fill
    ws_summary['A2'].font = light_blue_font
    ws_summary['B2'].font = light_blue_font
    ws_summary['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws_summary['B2'].alignment = Alignment(horizontal='center', vertical='center')
    ws_summary['A2'].border = thin_border
    ws_summary['B2'].border = thin_border
    ws_summary.row_dimensions[2].height = 25
    
    # Ma'lumotlar
    row = 3
    data = [
        ('Jami foydalanuvchilar', stats['total_users']),
        ('Jami so\'rovlar', stats['total_requests']),
        ('Yozma so\'rovlar', stats['total_text']),
        ('Fayl yuborishlar', stats['total_files']),
        ('Rasm yuborishlar', stats['total_images']),
        ('Ovozli xabarlar', stats['total_voice']),
        ('', ''),  # Bo'sh qator
        ('Kod tahlil (jami)', stats.get('total_code_reviews', 0)),
        ('Xatosiz kodlar', stats.get('total_positive', 0)),
        ('Xatoli kodlar', stats.get('total_negative', 0)),
    ]
    
    for idx, (label, value) in enumerate(data):
        cell_a = ws_summary[f'A{row}']
        cell_b = ws_summary[f'B{row}']
        cell_a.value = label
        cell_b.value = value
        
        # Border va alignment
        cell_a.border = thin_border
        cell_b.border = thin_border
        cell_a.alignment = Alignment(horizontal='left', vertical='center')
        cell_b.alignment = Alignment(horizontal='center', vertical='center')
        
        # Qator balandligi
        ws_summary.row_dimensions[row].height = 22
        
        # Alternativ rang - oq va kulrang
        if label:
            if idx % 2 == 0:
                cell_a.fill = light_gray_fill
                cell_b.fill = light_gray_fill
            else:
                cell_a.fill = white_fill
                cell_b.fill = white_fill
            cell_a.font = Font(size=11, color="1F4E78", name='Calibri')  # To'q ko'k matn
        else:
            cell_a.fill = white_fill
            cell_b.fill = white_fill
        
        # Raqamlar uchun bold va to'q ko'k
        if isinstance(value, int) and value > 0:
            cell_b.font = Font(bold=True, size=12, color="1F4E78")
        
        row += 1
    
    # Column width
    ws_summary.column_dimensions['A'].width = 32
    ws_summary.column_dimensions['B'].width = 18
    
    # Freeze panes
    ws_summary.freeze_panes = 'A3'
    
    # 2. FOYDALANUVCHILAR SHEET
    ws_users = wb.create_sheet("Foydalanuvchilar")
    
    # Title qatori - to'q ko'k
    ws_users.merge_cells('A1:M1')
    title_cell = ws_users['A1']
    title_cell.value = 'FOYDALANUVCHILAR RO\'YXATI'
    title_cell.fill = dark_blue_fill
    title_cell.font = Font(bold=True, color="FFFFFF", size=14, name='Calibri')
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    title_cell.border = medium_border
    ws_users.row_dimensions[1].height = 30
    
    # Headers - och ko'k (bir qatorda)
    headers = ['№', 'Foydalanuvchi Ismi', 'User ID', 'Jami So\'rov', 'Yozma Xabar', 'Yuborilgan Fayl', 'Yuborilgan Rasm', 'Ovozli Xabar', 'Kod OK', 'Kod Xato', 'Fayl Turlari', 'Birinchi Faoliyat', 'Oxirgi Faoliyat']
    for col, header in enumerate(headers, 1):
        cell = ws_users.cell(row=2, column=col, value=header)
        cell.fill = light_blue_fill
        cell.font = light_blue_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=False)
        cell.border = thin_border
    
    # Header qator balandligi - bir qator uchun
    ws_users.row_dimensions[2].height = 25
    
    # Ma'lumotlar
    for idx, user in enumerate(stats['top_users'], 3):
        # Ma'lumotlarni yozish
        cells_data = [
            (1, idx-2),  # #
            (2, user['name']),  # Ism
            (3, user['user_id']),  # User ID
            (4, user['total']),  # Jami
            (5, user['text']),  # Yozma
            (6, user['file']),  # Fayl
            (7, user['image']),  # Rasm
            (8, user['voice']),  # Ovoz
            (9, user.get('code_reviews_positive', 0)),  # Kod✅
            (10, user.get('code_reviews_negative', 0)),  # Kod❌
        ]
        
        for col, value in cells_data:
            cell = ws_users.cell(row=idx, column=col, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.font = Font(size=11, name='Calibri')
        
        # Ism - chapga va bold
        ws_users.cell(row=idx, column=2).alignment = Alignment(horizontal='left', vertical='center')
        ws_users.cell(row=idx, column=2).font = Font(bold=True, size=11, name='Calibri')
        
        # Fayl turlari - har birini alohida qatorga
        if user.get('files_by_type'):
            file_types_list = [f"{k.upper()}({v})" for k, v in sorted(user['files_by_type'].items(), key=lambda x: x[1], reverse=True)]
            # Har bir fayl turini yangi qatorga qo'yish
            file_types = '\n'.join(file_types_list)
            cell = ws_users.cell(row=idx, column=11, value=file_types)
            # Qator balandligini sozlash (har bir fayl turi uchun ~18 pixel)
            ws_users.row_dimensions[idx].height = max(25, len(file_types_list) * 18)
        else:
            cell = ws_users.cell(row=idx, column=11, value='-')
            ws_users.row_dimensions[idx].height = 25
        
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        cell.font = Font(size=10, name='Calibri')
        
        # Birinchi va oxirgi faoliyat
        for col, date_val in [(12, user.get('first_seen', '-')[:10] if user.get('first_seen') else '-'),
                               (13, user.get('last_seen', '-')[:10] if user.get('last_seen') else '-')]:
            cell = ws_users.cell(row=idx, column=col, value=date_val)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Rang berish - alternativ oq/kulrang
        if idx % 2 == 0:
            fill = light_gray_fill
        else:
            fill = white_fill
        
        for col in range(1, 14):
            current_cell = ws_users.cell(row=idx, column=col)
            current_cell.fill = fill
    
    # Column widths - avtomatik sozlash (header uzunligiga qarab)
    column_widths = {
        'A': 5,    # №
        'B': 22,   # Foydalanuvchi Ismi
        'C': 12,   # User ID
        'D': 12,   # Jami So'rov
        'E': 13,   # Yozma Xabar
        'F': 16,   # Yuborilgan Fayl
        'G': 16,   # Yuborilgan Rasm
        'H': 13,   # Ovozli Xabar
        'I': 9,    # Kod OK
        'J': 9,    # Kod Xato
        'K': 25,   # Fayl Turlari
        'L': 17,   # Birinchi Faoliyat
        'M': 16    # Oxirgi Faoliyat
    }
    
    for col, width in column_widths.items():
        ws_users.column_dimensions[col].width = width
    
    # Freeze panes - title va header qatorlarini qotirish
    ws_users.freeze_panes = 'A3'
    
    # 3. KUNLIK STATISTIKA SHEET
    ws_daily = wb.create_sheet("Kunlik Statistika")
    
    # Headers
    ws_daily['A1'] = 'Sana'
    ws_daily['B1'] = 'So\'rovlar Soni'
    ws_daily['A1'].fill = dark_blue_fill
    ws_daily['B1'].fill = dark_blue_fill
    ws_daily['A1'].font = dark_blue_font
    ws_daily['B1'].font = dark_blue_font
    ws_daily['A1'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=False)
    ws_daily['B1'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=False)
    ws_daily['A1'].border = medium_border
    ws_daily['B1'].border = medium_border
    ws_daily.row_dimensions[1].height = 25
    
    # Ma'lumotlar (oxirgi 30 kun)
    sorted_dates = sorted(stats['daily_stats'].items(), reverse=True)[:30]
    for idx, (date, count) in enumerate(sorted_dates, 2):
        cell_a = ws_daily.cell(row=idx, column=1, value=date)
        cell_b = ws_daily.cell(row=idx, column=2, value=count)
        
        # Border va alignment
        cell_a.border = thin_border
        cell_b.border = thin_border
        cell_a.alignment = Alignment(horizontal='center', vertical='center')
        cell_b.alignment = Alignment(horizontal='center', vertical='center')
        
        # Qator balandligi
        ws_daily.row_dimensions[idx].height = 22
        
        # Rang berish
        if count > 10:
            cell_a.fill = green_fill
            cell_b.fill = green_fill
        elif count > 5:
            cell_a.fill = yellow_fill
            cell_b.fill = yellow_fill
        else:
            cell_a.fill = white_fill
            cell_b.fill = white_fill
        
        # Raqam bold
        cell_b.font = Font(bold=True, size=11, color="000000")
    
    ws_daily.column_dimensions['A'].width = 13
    ws_daily.column_dimensions['B'].width = 15
    
    # Freeze panes
    ws_daily.freeze_panes = 'A2'
    
    # 4. FAYL TURLARI SHEET
    if stats['files_by_type']:
        ws_files = wb.create_sheet("Fayl Turlari")
        
        # Headers
        ws_files['A1'] = 'Fayl Turi'
        ws_files['B1'] = 'Soni'
        ws_files['C1'] = 'Foiz'
        ws_files['A1'].fill = dark_blue_fill
        ws_files['B1'].fill = dark_blue_fill
        ws_files['C1'].fill = dark_blue_fill
        ws_files['A1'].font = dark_blue_font
        ws_files['B1'].font = dark_blue_font
        ws_files['C1'].font = dark_blue_font
        ws_files['A1'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=False)
        ws_files['B1'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=False)
        ws_files['C1'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=False)
        ws_files['A1'].border = medium_border
        ws_files['B1'].border = medium_border
        ws_files['C1'].border = medium_border
        ws_files.row_dimensions[1].height = 25
        
        # Ma'lumotlar
        sorted_files = sorted(stats['files_by_type'].items(), key=lambda x: x[1], reverse=True)
        total_files = sum(count for _, count in sorted_files)
        
        for idx, (file_type, count) in enumerate(sorted_files, 2):
            cell_a = ws_files.cell(row=idx, column=1, value=file_type.upper())
            cell_b = ws_files.cell(row=idx, column=2, value=count)
            percentage = (count / total_files * 100) if total_files > 0 else 0
            cell_c = ws_files.cell(row=idx, column=3, value=f"{percentage:.1f}%")
            
            # Border va alignment
            cell_a.border = thin_border
            cell_b.border = thin_border
            cell_c.border = thin_border
            cell_a.alignment = Alignment(horizontal='left', vertical='center')
            cell_b.alignment = Alignment(horizontal='center', vertical='center')
            cell_c.alignment = Alignment(horizontal='center', vertical='center')
            
            # Qator balandligi
            ws_files.row_dimensions[idx].height = 24
            
            # Raqam bold
            cell_b.font = Font(bold=True, size=11)
            cell_c.font = Font(bold=True, size=11)
            
            # Rang berish
            if percentage > 30:
                fill = green_fill  # Yashil
            elif percentage > 10:
                fill = yellow_fill  # Sariq
            else:
                fill = white_fill  # Oq
            
            cell_a.fill = fill
            cell_b.fill = fill
            cell_c.fill = fill
        
        ws_files.column_dimensions['A'].width = 15
        ws_files.column_dimensions['B'].width = 12
        ws_files.column_dimensions['C'].width = 12
        
        # Freeze panes
        ws_files.freeze_panes = 'A2'
    
    # Faylni saqlash
    wb.save(filename)
    return filename

def generate_user_details_excel(user_stats, filename='user_details.xlsx'):
    """Bitta foydalanuvchi uchun batafsil Excel"""
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Foydalanuvchi Ma'lumotlari"
    
    # Header style
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    
    # Title
    ws['A1'] = f"FOYDALANUVCHI: {user_stats['name']}"
    ws['A1'].font = Font(bold=True, size=16)
    ws.merge_cells('A1:B1')
    
    # Ma'lumotlar
    ws['A3'] = 'Ko\'rsatkich'
    ws['B3'] = 'Qiymat'
    ws['A3'].fill = header_fill
    ws['B3'].fill = header_fill
    ws['A3'].font = header_font
    ws['B3'].font = header_font
    ws['A3'].alignment = Alignment(horizontal='center', vertical='center')
    ws['B3'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Border style
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    ws['A3'].border = thin_border
    ws['B3'].border = thin_border
    
    row = 4
    data = [
        ('User ID', user_stats['user_id']),
        ('Jami so\'rovlar', user_stats['total']),
        ('Yozma', user_stats['text']),
        ('Fayl', user_stats['file']),
        ('Rasm', user_stats['image']),
        ('Ovoz', user_stats['voice']),
    ]
    
    for label, value in data:
        cell_a = ws[f'A{row}']
        cell_b = ws[f'B{row}']
        cell_a.value = label
        cell_b.value = value
        cell_a.border = thin_border
        cell_b.border = thin_border
        cell_a.alignment = Alignment(horizontal='left', vertical='center')
        cell_b.alignment = Alignment(horizontal='center', vertical='center')
        if isinstance(value, int):
            cell_b.font = Font(bold=True)
        row += 1
    
    # Fayl turlari
    if user_stats.get('files_by_type'):
        row += 2
        ws[f'A{row}'] = 'Fayl Turlari'
        ws[f'A{row}'].font = Font(bold=True, size=12)
        row += 1
        
        ws[f'A{row}'] = 'Tur'
        ws[f'B{row}'] = 'Soni'
        ws[f'A{row}'].fill = header_fill
        ws[f'B{row}'].fill = header_fill
        ws[f'A{row}'].font = header_font
        ws[f'B{row}'].font = header_font
        ws[f'A{row}'].alignment = Alignment(horizontal='center', vertical='center')
        ws[f'B{row}'].alignment = Alignment(horizontal='center', vertical='center')
        ws[f'A{row}'].border = thin_border
        ws[f'B{row}'].border = thin_border
        row += 1
        
        for file_type, count in user_stats['files_by_type'].items():
            cell_a = ws[f'A{row}']
            cell_b = ws[f'B{row}']
            cell_a.value = file_type.upper()
            cell_b.value = count
            cell_a.border = thin_border
            cell_b.border = thin_border
            cell_a.alignment = Alignment(horizontal='left', vertical='center')
            cell_b.alignment = Alignment(horizontal='center', vertical='center')
            cell_b.font = Font(bold=True)
            row += 1
    
    ws.column_dimensions['A'].width = 32
    ws.column_dimensions['B'].width = 18
    
    wb.save(filename)
    return filename
