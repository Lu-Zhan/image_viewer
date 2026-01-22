import io
from pathlib import Path
from PIL import Image
from typing import Dict, List, Optional

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Table, TableStyle, Paragraph, Spacer, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from utils.image_processing import (
    load_and_process_image,
    check_image_exists,
    get_aspect_ratio,
    draw_all_crop_boxes_on_image,
    filter_visible_methods,
)
from utils.mask import load_mask, apply_mask_to_image


def pil_image_to_rl_image(pil_img: Image.Image, max_width: float, max_height: float) -> RLImage:
    """
    将PIL Image转换为reportlab Image对象
    参数:
        pil_img: PIL Image对象
        max_width: 最大宽度（点）
        max_height: 最大高度（点）
    返回:
        reportlab Image对象
    """
    # 保存到BytesIO
    img_buffer = io.BytesIO()
    pil_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # 计算合适的尺寸，保持宽高比
    img_width, img_height = pil_img.size
    aspect_ratio = img_width / img_height
    
    # 按宽度或高度限制缩放
    if img_width / max_width > img_height / max_height:
        # 宽度限制
        width = max_width
        height = max_width / aspect_ratio
    else:
        # 高度限制
        height = max_height
        width = max_height * aspect_ratio
    
    return RLImage(img_buffer, width=width, height=height)


class ColoredSquare(Flowable):
    """带颜色边框的方块Flowable，用于Close View标题"""
    def __init__(self, size=3*mm, color='#00ff00'):
        Flowable.__init__(self)
        self.size = size
        self.color = colors.HexColor(color)
        self.width = size
        self.height = size
    
    def draw(self):
        """绘制带黑边的彩色方块"""
        self.canv.setFillColor(self.color)
        self.canv.setStrokeColor(colors.black)
        self.canv.setLineWidth(0.5)
        self.canv.rect(0, 0, self.size, self.size, fill=1, stroke=1)


def generate_pdf_from_current_view(
    samples: List[Dict],
    methods: List[Dict],
    base_dir: Path,
    start_idx: int,
    num_rows: int,
    show_method_name: bool,
    show_text: bool,
    show_sample_name: bool,
    show_descriptions: bool,
    close_view_enabled: bool,
    crop_data: Dict,
    preserve_aspect_ratio: bool,
    lang: Dict,
    use_mask: bool = False,
    darken_factor: float = 0.5,
    image_width: int = 800,
    visible_methods: Optional[List[str]] = None
) -> bytes:
    """
    生成当前视图的PDF
    返回: PDF二进制数据
    """
    overlay_opacity = darken_factor  # Rename for clarity in function

    # 使用过滤后的方法列表
    visible_methods_list = filter_visible_methods(methods, visible_methods) if visible_methods else methods

    # 创建PDF缓冲区
    buffer = io.BytesIO()
    
    # 使用横向A4页面
    page_width, page_height = landscape(A4)
    
    # 创建PDF文档
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1*mm,
        rightMargin=1*mm,
        topMargin=1*mm,
        bottomMargin=1*mm
    )
    
    # 获取样式
    styles = getSampleStyleSheet()
    
    # 创建自定义样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=3*mm,
        alignment=1  # 居中
    )
    
    text_style = ParagraphStyle(
        'CustomText',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=1*mm,
        spaceBefore=1*mm
    )
    
    method_name_style = ParagraphStyle(
        'MethodName',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,  # 居中
        spaceAfter=0.5*mm
    )
    
    # 构建内容
    elements = []
    
    # 确定要显示的样本范围
    end_idx = min(start_idx + num_rows, len(samples))
    selected_samples = samples[start_idx:end_idx]
    
    # 计算可用宽度
    available_width = page_width - 2*mm  # 减去左右边距（1mm×2）
    
    # 计算列数
    num_methods = len(visible_methods_list)
    num_cols = num_methods
    
    # 列间距（约10px = 3.5mm）
    col_spacing = 3.5*mm
    
    # 每列图片的最大宽度和高度
    # 总间距 = (列数-1) × 列间距
    total_spacing = (num_cols - 1) * col_spacing if num_cols > 1 else 0
    col_width = (available_width - total_spacing) / num_cols
    max_img_height = 60*mm  # 主图片的最大高度
    
    for row_idx, sample in enumerate(selected_samples):
        actual_sample_idx = start_idx + row_idx
        sample_crop_data = crop_data.get(actual_sample_idx, None)
        
        # Sample名称标题（左对齐）
        if show_sample_name:
            sample_title_style = ParagraphStyle(
                'SampleTitle',
                parent=styles['Normal'],
                fontSize=10,
                alignment=0,  # 左对齐
                leftIndent=0,
                spaceBefore=2*mm if row_idx > 0 else 0,
                spaceAfter=2*mm
            )
            sample_name_para = Paragraph(f"<b>Sample: {sample['name']}</b>", sample_title_style)
            elements.append(sample_name_para)
        
        # 方法名称行（只在第一个样本时显示）
        if show_method_name and row_idx == 0:
            method_names_row = []
            for method in visible_methods_list:
                method_names_row.append(Paragraph(method['name'], method_name_style))

            # 创建方法名称表格
            name_table = Table([method_names_row], colWidths=[col_width] * num_cols)
            name_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (0, -1), 0),                    # 第一列左边无padding
                ('RIGHTPADDING', (-1, 0), (-1, -1), 0),                 # 最后一列右边无padding
                ('LEFTPADDING', (1, 0), (-1, -1), col_spacing/2),       # 其他列左边padding
                ('RIGHTPADDING', (0, 0), (-2, -1), col_spacing/2),      # 其他列右边padding
            ]))
            elements.append(name_table)
            elements.append(Spacer(1, 2*mm))
        
        # 收集主图片
        images_row = []
        for method in methods:
            method_name = method["name"]
            
            if method_name not in sample["images"]:
                images_row.append(Paragraph("N/A", text_style))
                continue
            
            image_rel_path = sample["images"][method_name]
            image_path = base_dir / image_rel_path
            
            if not check_image_exists(base_dir, image_rel_path):
                images_row.append(Paragraph("Missing", text_style))
                continue
            
            try:
                # 加载并处理图片
                processed_img, _, _ = load_and_process_image(
                    image_path, image_width, preserve_aspect_ratio
                )
                
                if processed_img is not None:
                    # 应用 mask（如果启用且存在）
                    if use_mask and "mask" in sample and sample["mask"]:
                        mask_path = base_dir / sample["mask"]
                        if check_image_exists(base_dir, sample["mask"]):
                            mask_img = load_mask(mask_path, processed_img.size)
                            if mask_img is not None:
                                processed_img = apply_mask_to_image(processed_img, mask_img, overlay_opacity)
                    
                    # 如果有crop data且close view启用，绘制裁剪框
                    if close_view_enabled and sample_crop_data:
                        try:
                            original_img = Image.open(image_path)
                            original_size = original_img.size
                            display_size = processed_img.size
                            crops = sample_crop_data.get('crops', [])
                            if crops:
                                processed_img = draw_all_crop_boxes_on_image(
                                    processed_img, crops, original_size, display_size
                                )
                        except Exception:
                            pass
                    
                    rl_img = pil_image_to_rl_image(processed_img, col_width, max_img_height)
                    images_row.append(rl_img)
                else:
                    images_row.append(Paragraph("Error", text_style))
            except Exception as e:
                images_row.append(Paragraph("Error", text_style))

        # 创建图片表格，添加行间距
        img_table = Table([images_row], colWidths=[col_width] * num_cols, rowHeights=None)
        img_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, -1), 0),                    # 第一列左边无padding
            ('RIGHTPADDING', (-1, 0), (-1, -1), 0),                 # 最后一列右边无padding
            ('LEFTPADDING', (1, 0), (-1, -1), col_spacing/2),       # 其他列左边padding
            ('RIGHTPADDING', (0, 0), (-2, -1), col_spacing/2),      # 其他列右边padding
            ('TOPPADDING', (0, 0), (-1, -1), 1*mm),                 # 上方padding
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),              # 下方padding
        ]))
        elements.append(img_table)
        
        # 显示Close Views（如果启用）
        if close_view_enabled and sample_crop_data:
            crops = sample_crop_data.get('crops', [])
            
            for crop_idx, crop in enumerate(crops):
                elements.append(Spacer(1, 1*mm))
                
                # 获取crop颜色和ID
                color = crop['color']
                crop_id = crop.get('id', f'crop_{crop_idx}')
                
                # 创建Close View标题样式（左对齐，不加粗）
                close_view_style = ParagraphStyle(
                    'CloseViewTitle',
                    parent=styles['Normal'],
                    fontSize=8,
                    alignment=0,  # 左对齐
                    leftIndent=0,
                    spaceAfter=2*mm
                )
                
                # 创建彩色方块
                color_square = ColoredSquare(size=2*mm, color=color)
                
                # 创建标题文字（不加粗）
                title_text = Paragraph(f"Close View #{crop_idx + 1}", close_view_style)
                
                # 使用Table组合方块和文字，左侧padding与第一列图片对齐
                first_col_left_padding = (available_width - total_spacing) / num_cols
                # 计算标题表格的宽度和位置，使其与图片表格第一列对齐
                title_row = [[color_square, title_text]]
                title_table = Table(
                    title_row,
                    colWidths=[4*mm, available_width - 4*mm],
                    rowHeights=[4*mm]
                )
                title_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                
                elements.append(title_table)
                
                # 收集裁剪后的图片（Close View不应用mask）
                cropped_row = []
                for method in visible_methods_list:
                    method_name = method["name"]
                    if method_name in crop.get('cropped_images', {}):
                        cropped_img = crop['cropped_images'][method_name]
                        rl_img = pil_image_to_rl_image(cropped_img, col_width, max_img_height)
                        cropped_row.append(rl_img)
                    else:
                        cropped_row.append(Paragraph("N/A", text_style))

                # 创建裁剪图片表格，添加行间距
                crop_table = Table([cropped_row], colWidths=[col_width] * num_cols, rowHeights=None)
                crop_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (0, -1), 0),                    # 第一列左边无padding
                    ('RIGHTPADDING', (-1, 0), (-1, -1), 0),                 # 最后一列右边无padding
                    ('LEFTPADDING', (1, 0), (-1, -1), col_spacing/2),       # 其他列左边padding
                    ('RIGHTPADDING', (0, 0), (-2, -1), col_spacing/2),      # 其他列右边padding
                    ('TOPPADDING', (0, 0), (-1, -1), 1*mm),                 # 上方padding
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),              # 下方padding
                ]))
                elements.append(crop_table)
                
                # 添加Close View之间的行间距
                if crop_idx < len(crops) - 1:
                    elements.append(Spacer(1, 2*mm))
        
        # 显示样本文本
        if show_text and "text" in sample and sample["text"]:
            elements.append(Spacer(1, 1*mm))
            if show_sample_name:
                text_content = f"<b>{sample['name']}</b> | Text: {sample['text']}"
            else:
                text_content = f"Text: {sample['text']}"
            elements.append(Paragraph(text_content, text_style))
        
        # 样本之间添加分隔
        if row_idx < len(selected_samples) - 1:
            elements.append(Spacer(1, 3*mm))
    
    # 方法描述（在最后显示）
    if show_descriptions:
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(lang['method_desc_title'], title_style))
        
        desc_data = []
        for method in methods:
            desc = method.get('description', '')
            desc_data.append([
                Paragraph(f"<b>{method['name']}</b>", text_style),
                Paragraph(desc if desc else "-", text_style)
            ])

        desc_table = Table(desc_data, colWidths=[50*mm, available_width - 55*mm])
        desc_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),
        ]))
        elements.append(desc_table)
    
    # 构建PDF
    doc.build(elements)
    
    # 获取PDF数据
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data
