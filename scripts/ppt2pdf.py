import win32com.client
from pptx import Presentation
import os
import sys

def pptx_to_pdf_windows(pptx_path, pdf_path=None):
    """
    Windows 平台 PPTX 转 PDF（依赖本地 PowerPoint）
    :param pptx_path: 输入 PPTX 文件路径（绝对路径或相对路径）
    :param pdf_path: 输出 PDF 文件路径（默认与PPTX同目录、同名）
    :return: 转换成功返回 True，失败返回 False
    """
    # 验证文件合法性
    if not os.path.exists(pptx_path):
        print(f"错误：文件不存在 -> {pptx_path}")
        return False
    
    # 只对 .pptx 文件进行 python-pptx 验证，.ppt 文件跳过
    if pptx_path.lower().endswith('.pptx'):
        try:
            Presentation(pptx_path)  # 验证文件是否为有效 PPTX
        except Exception as e:
            print(f"错误：无效的 PPTX 文件 -> {e}")
            return False

    # 默认输出路径（与PPTX同目录、同名）
    if not pdf_path:
        pdf_path = os.path.splitext(pptx_path)[0] + ".pdf"

    powerpoint = None
    presentation = None
    exported = False

    try:
        # 启动 PowerPoint 应用（后台运行，不显示界面）
        powerpoint = win32com.client.DispatchEx("PowerPoint.Application")
        powerpoint.Visible = 0  # 后台运行
        powerpoint.DisplayAlerts = 0  # 禁用警告弹窗

        # 打开 PPTX 文件
        presentation = powerpoint.Presentations.Open(
            os.path.abspath(pptx_path),  # 必须传入绝对路径
            WithWindow=False  # 不打开窗口
        )

        # 保存为 PDF（FileFormat=32 对应 PDF 格式）
        presentation.SaveAs(os.path.abspath(pdf_path), FileFormat=32)
        exported = True

    except Exception as e:
        print(f"转换失败：{e}")

    finally:
        # 关闭资源（关键：避免 PowerPoint 进程残留）
        if presentation is not None:
            try:
                presentation.Close()
            except Exception:
                pass
        if powerpoint is not None:
            try:
                powerpoint.Quit()
            except Exception:
                pass

    if exported and os.path.exists(pdf_path):
        print(f"转换成功！PDF 路径：{pdf_path}")
        return True

    return False


def batch_convert_folder(folder_path):
    """
    批量转换文件夹中的所有PPTX文件为PDF
    :param folder_path: 文件夹路径
    """
    if not os.path.exists(folder_path):
        print(f"错误：文件夹不存在 -> {folder_path}")
        return
    
    # 获取所有pptx文件
    ppt_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.ppt', '.pptx'))]
    
    if not ppt_files:
        print("未找到任何PPT/PPTX文件")
        return
    
    print(f"找到 {len(ppt_files)} 个PPT/PPTX文件，开始转换...\n")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for i, filename in enumerate(ppt_files, 1):
        pptx_path = os.path.join(folder_path, filename)
        print(f"[{i}/{len(ppt_files)}] 正在转换: {filename}")

        pdf_path = os.path.splitext(pptx_path)[0] + ".pdf"
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            print(f"已存在PDF，跳过：{pdf_path}")
            skip_count += 1
            print()
            continue
        
        if pptx_to_pdf_windows(pptx_path):
            success_count += 1
        else:
            fail_count += 1
        print()
    
    print(f"转换完成！成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}")


# 示例调用
if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        if os.path.isdir(input_path):
            batch_convert_folder(input_path)
        elif os.path.isfile(input_path):
            pptx_to_pdf_windows(input_path)
        else:
            print(f"错误：路径不存在 -> {input_path}")
    else:
        # 默认行为（保留用于测试或无参数调用）
        print("用法: python ppt2pdf.py <文件或文件夹路径>")
        # 批量转换社会心理学2025文件夹
        batch_convert_folder(r"c:\Users\LENOVO\Desktop\Fall-Network\社会心理学2025")
        # 或单个文件转换：pptx_to_pdf_windows("input.pptx", "output.pdf")