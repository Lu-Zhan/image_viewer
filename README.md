# 图片比较可视化工具

基于 Streamlit 和 Pillow 的图片对比可视化应用程序。

## 功能特点

- 📁 通过 JSON 配置文件加载多组图片
- 🖼️ 自动检测并处理不同宽高比的图片
- ✂️ 智能裁剪至接近 1:1 的比例
- 📊 并排对比多种方法的结果
- 🎨 可调节图片显示宽度（默认 512px）
- 🔄 轻松切换不同样本
- 🔍 **Close View 功能**：支持任意长宽比裁剪，精细对比局部细节
- 📋 **Reference 查看**：支持显示参考图片，便于对比生成结果与原始参考
- 🎭 **Mask 功能**：支持对图片应用 mask 效果，mask > 0 区域正常显示，其余区域变暗
- 📥 **PDF 导出**：一键导出当前页面为 PDF 文件，包含所有图片和 Close View

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

1. 准备 JSON 配置文件（参考 sample.json）
2. 运行应用：
```bash
streamlit run app.py
```
3. 在浏览器中上传 JSON 文件并查看图片对比

## JSON 格式

```json
{
  "base_dir": "图片基础目录路径",
  "methods": [
    {
      "name": "方法名称",
      "description": "方法描述"
    }
  ],
  "samples": [
    {
      "name": "样本名称",
      "text": "样本文本",
      "reference": "参考图片路径.jpg",
      "mask": "mask 图片路径.png",
      "images": {
        "方法名称": "相对图片路径.jpg"
      }
    }
  ]
}
```

**字段说明**：
- `reference`（可选）：参考图片路径，用于对比
- `mask`（可选）：mask 图片路径，启用 Mask 功能后，mask > 0 的区域正常显示，其余区域变暗
- `text`（可选）：样本描述文本
