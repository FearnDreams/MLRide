"""
可视化组件执行器

该模块实现了数据可视化相关的组件执行器，用于生成各种图表和可视化结果。
"""

import logging
import json
import traceback
import os
from typing import Dict, Any, List
from .executors import BaseComponentExecutor, ExecutionResult

logger = logging.getLogger(__name__)

# 定义通用的中文字体设置函数
def setup_chinese_font():
    """配置matplotlib支持中文字体"""
    import matplotlib.pyplot as plt
    import matplotlib
    import platform
    
    # 尝试多种中文字体，提高兼容性
    chinese_fonts = ['SimHei', 'Microsoft YaHei', 'STHeiti', 'WenQuanYi Micro Hei', 'NSimSun', 
                    'FangSong', 'KaiTi', 'PingFang SC', 'Heiti SC', 'Source Han Sans CN', 
                    'Noto Sans CJK SC', 'Noto Sans SC', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
    
    plt.rcParams['font.sans-serif'] = chinese_fonts
    plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
    
    # PDF和PS支持
    matplotlib.rcParams['pdf.fonttype'] = 42
    matplotlib.rcParams['ps.fonttype'] = 42
    
    # 检测操作系统以选择合适的字体路径
    system = platform.system()
    font_paths = []
    
    if system == 'Linux':
        # Linux系统字体路径
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Debian/Ubuntu
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",           # CentOS/RHEL
            "/usr/share/fonts/TTF/DejaVuSans.ttf",              # Arch Linux
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",   # 文泉驿微米黑
            "/usr/share/fonts/chinese/TrueType/SimHei.ttf",     # 黑体
            "/usr/share/fonts/chinese/TrueType/SimSun.ttc"      # 宋体
        ]
    elif system == 'Windows':
        # Windows系统字体路径
        font_paths = [
            "C:\\Windows\\Fonts\\simhei.ttf",        # 黑体
            "C:\\Windows\\Fonts\\simsun.ttc",        # 宋体
            "C:\\Windows\\Fonts\\msyh.ttc",          # 微软雅黑
            "C:\\Windows\\Fonts\\simfang.ttf"        # 仿宋
        ]
    elif system == 'Darwin':  # macOS
        # macOS系统字体路径
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",     # 苹方
            "/Library/Fonts/Arial Unicode.ttf",       # Arial Unicode
            "/System/Library/Fonts/STHeiti Light.ttc" # 黑体
        ]
    
    # 尝试添加各个字体
    added_font = False
    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                matplotlib.font_manager.fontManager.addfont(font_path)
                logger.info(f"成功添加字体: {font_path}")
                added_font = True
        except Exception as e:
            logger.warning(f"添加字体失败 {font_path}: {e}")
    
    # 尝试刷新字体缓存
    try:
        matplotlib.font_manager._load_fontmanager(try_read_cache=False)
        logger.info("已刷新字体缓存")
    except Exception as e:
        logger.warning(f"刷新字体缓存失败: {e}")
    
    # 如果没有添加任何字体或需要额外设置
    if not added_font:
        try:
            # 使用通用系统设置
            import matplotlib.font_manager as fm
            # 搜索所有可用字体
            all_fonts = [f.name for f in fm.fontManager.ttflist]
            # 查找任何中文字体
            chinese_available = [f for f in all_fonts if any(cf in f for cf in ['Hei', 'Micro', 'SimSun', 'Song', 'YaHei', 'Ming'])]
            
            if chinese_available:
                plt.rcParams['font.sans-serif'] = chinese_available + plt.rcParams['font.sans-serif']
                logger.info(f"已设置系统中已有的中文字体: {chinese_available[:3]}")
        except Exception as e:
            logger.warning(f"中文字体回退设置失败: {e}")

class BarChartGenerator(BaseComponentExecutor):
    """柱状图生成器
    
    生成柱状图，展示分类数据的分布或比较。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成柱状图
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
            parameters: 参数，包括:
                - x_column: X轴列名
                - y_column: Y轴列名
                - title: 图表标题
                - orientation: 方向（vertical/horizontal）
                
        Returns:
            ExecutionResult: 执行结果，包含生成的柱状图
        """
        try:
            # 获取输入数据
            if 'dataset' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['dataset']
            
            # 获取参数
            x_column = parameters.get('x_column', '')
            y_column = parameters.get('y_column', '')
            title = parameters.get('title', '柱状图')
            orientation = parameters.get('orientation', 'vertical')
            color = parameters.get('color', 'blue')
            
            if not x_column and not y_column:
                return ExecutionResult(
                    success=False,
                    error_message="必须指定至少一个列作为X轴或Y轴"
                )
            
            # 直接在Python中执行
            code = """
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import io
import base64
import os

# 应用中文字体设置
try:
    setup_chinese_font()
except Exception as e:
    logger.warning(f"设置中文字体失败: {str(e)}")
    # 基本字体设置，确保有备选方案
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

# 解析输入数据集
if isinstance(dataset, dict) and 'data' in dataset:
    if isinstance(dataset['data'], str):
        df = pd.read_json(dataset['data'], orient='split')
    else:
        df = pd.DataFrame(dataset['data'])
else:
    df = pd.DataFrame(dataset)

# 如果没有指定y_column，则进行频次统计
if not y_column:
    if x_column not in df.columns:
        return ExecutionResult(
            success=False,
            error_message=f"找不到列: {x_column}"
        )
    # 获取分类频次
    counts = df[x_column].value_counts().reset_index()
    counts.columns = ['category', 'count']
    x_data = counts['category']
    y_data = counts['count']
    if orientation == 'vertical':
        plt.figure(figsize=(10, 6))
        plt.bar(x_data, y_data, color=color)
        plt.xlabel(x_column)
        plt.ylabel('频次')
    else:
        plt.figure(figsize=(8, len(x_data) * 0.5 + 2))
        plt.barh(x_data, y_data, color=color)
        plt.xlabel('频次')
        plt.ylabel(x_column)

# 如果同时指定了x_column和y_column
elif x_column and y_column:
    if x_column not in df.columns or y_column not in df.columns:
        return ExecutionResult(
            success=False,
            error_message=f"找不到列: {x_column if x_column not in df.columns else y_column}"
        )
    
    # 如果y_column是数值类型，直接绘制
    if pd.api.types.is_numeric_dtype(df[y_column]):
        if orientation == 'vertical':
            plt.figure(figsize=(12, 6))
            plt.bar(df[x_column], df[y_column], color=color)
            plt.xlabel(x_column)
            plt.ylabel(y_column)
            # 如果x轴标签太多，旋转它们
            if len(df[x_column].unique()) > 10:
                plt.xticks(rotation=45, ha='right')
        else:
            plt.figure(figsize=(8, len(df[x_column].unique()) * 0.5 + 2))
            plt.barh(df[x_column], df[y_column], color=color)
            plt.xlabel(y_column)
            plt.ylabel(x_column)
    # 如果y_column不是数值类型，做分组统计
    else:
        # 获取交叉表
        cross_tab = pd.crosstab(df[x_column], df[y_column])
        if orientation == 'vertical':
            plt.figure(figsize=(12, 6))
            cross_tab.plot(kind='bar', ax=plt.gca())
            plt.xlabel(x_column)
            plt.ylabel('计数')
            plt.legend(title=y_column)
            # 如果x轴标签太多，旋转它们
            if len(cross_tab.index) > 10:
                plt.xticks(rotation=45, ha='right')
        else:
            plt.figure(figsize=(8, len(cross_tab.index) * 0.8 + 2))
            cross_tab.plot(kind='barh', ax=plt.gca())
            plt.xlabel('计数')
            plt.ylabel(x_column)
            plt.legend(title=y_column)

plt.title(title)
plt.tight_layout()

# 保存图像为base64
buf = io.BytesIO()
plt.savefig(buf, format='png', dpi=300)
buf.seek(0)
img_str = base64.b64encode(buf.read()).decode('utf-8')
plt.close()

# 返回结果
result = {
    'chart_type': 'bar',
    'title': title,
    'image': img_str,
    'x_column': x_column,
    'y_column': y_column
}
"""
            
            # 创建一个本地变量字典，包含必要的变量
            local_vars = {
                'dataset': dataset,
                'x_column': x_column,
                'y_column': y_column,
                'title': title,
                'orientation': orientation,
                'color': color,
                'logger': logger,
                'setup_chinese_font': setup_chinese_font,
                'ExecutionResult': ExecutionResult
            }
            
            # 执行代码
            try:
                exec(code, globals(), local_vars)
                result = local_vars.get('result', {})
                
                return ExecutionResult(
                    success=True,
                    outputs=result,
                    logs=["柱状图生成完成"]
                )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error_message=f"生成柱状图失败: {str(e)}",
                    logs=[traceback.format_exc()]
                )
                
        except Exception as e:
            logger.error(f"执行柱状图生成器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class LineChartGenerator(BaseComponentExecutor):
    """折线图生成器
    
    生成折线图，展示数据的趋势和变化。
    能够接收普通数据集或ROC曲线数据并进行可视化。
    """
    
    def _fig_to_base64(self, plt, dpi=100, quality=90):
        """将matplotlib图形转换为base64编码的字符串
        
        Args:
            plt: matplotlib pyplot对象
            dpi: 图像DPI（每英寸点数），影响图像质量和大小
            quality: JPEG压缩质量（仅当format='jpg'时使用）
            
        Returns:
            str: 图像的base64编码字符串
        """
        
        import io
        import base64
        
        # 确保中文正确显示
        try:
            # 尝试应用中文字体设置
            setup_chinese_font()
        except:
            # 如果出现错误，使用基本设置
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'sans-serif']
            plt.rcParams['axes.unicode_minus'] = False
        
        # 确保图形尺寸合适，避免模态框内需要滚动条
        figsize = plt.gcf().get_size_inches()
        if figsize[0] > 12 or figsize[1] > 8:
            # 重新设置图形尺寸，保持原比例但最大化在12x8范围内
            scale = min(12/figsize[0], 8/figsize[1])
            new_figsize = (figsize[0] * scale, figsize[1] * scale)
            plt.gcf().set_size_inches(new_figsize)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    
    def _compress_image_data(self, base64_str, target_size=500000):
        """压缩base64编码的图像数据
        
        Args:
            base64_str: 原始base64编码字符串
            target_size: 目标大小（字节数）
            
        Returns:
            str: 压缩后的base64编码字符串，如果失败则返回None
        """
        try:
            import base64
            import io
            from PIL import Image
            
            # 解码base64字符串
            img_data = base64.b64decode(base64_str)
            img_buf = io.BytesIO(img_data)
            img = Image.open(img_buf)
            
            # 计算当前大小
            current_size = len(base64_str)
            
            # 如果已经小于目标大小，直接返回
            if current_size <= target_size:
                return base64_str
                
            # 确定压缩质量和尺寸缩放因子
            quality = 85
            scale_factor = 1.0
            
            # 尝试不同的压缩参数，直到满足大小要求
            for attempt in range(5):  # 最多尝试5次
                # 缩放图像
                if scale_factor < 1.0:
                    new_width = int(img.width * scale_factor)
                    new_height = int(img.height * scale_factor)
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                else:
                    resized_img = img
                
                # 保存为JPEG格式（有损压缩）
                output_buf = io.BytesIO()
                resized_img.convert('RGB').save(output_buf, format='JPEG', quality=quality)
                output_buf.seek(0)
                
                # 编码为base64
                compressed_data = base64.b64encode(output_buf.getvalue()).decode('utf-8')
                
                # 检查是否达到目标大小
                if len(compressed_data) <= target_size:
                    return compressed_data
                
                # 调整参数用于下一次尝试
                if quality > 40:
                    quality -= 10  # 降低质量
                else:
                    scale_factor *= 0.8  # 缩小图像
            
            # 最后尝试：极端压缩
            output_buf = io.BytesIO()
            img.resize((img.width // 2, img.height // 2), Image.LANCZOS).convert('RGB').save(
                output_buf, format='JPEG', quality=30)
            output_buf.seek(0)
            return base64.b64encode(output_buf.getvalue()).decode('utf-8')
            
        except Exception as e:
            logger.warning(f"压缩图像失败: {str(e)}")
            return None
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成折线图
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集（常规数据）
                - roc_data: ROC曲线数据（来自ROCCurveGenerator）
            parameters: 参数，包括:
                - x_column: X轴列名（使用dataset时）
                - y_columns: Y轴列名（使用dataset时，可以是多个，用逗号分隔）
                - title: 图表标题
                - show_markers: 是否显示标记点
                - source_type: 数据源类型（'dataset' 或 'roc'）
                
        Returns:
            ExecutionResult: 执行结果，包含生成的折线图
        """
        import matplotlib.pyplot as plt
        
        try:
            # 获取参数
            source_type = parameters.get('source_type', 'dataset')
            title = parameters.get('title', '折线图')
            show_markers = parameters.get('show_markers', True)
            
            # 初始化日志列表
            logs = []
            
            # 引入必要的库
            
            
            # 设置中文支持
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']  # 尝试多种字体
            plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

            # 加载数据后添加额外的字体处理
            # 确保即使在容器环境中也能正确显示中文
            import matplotlib
            matplotlib.rcParams['pdf.fonttype'] = 42
            matplotlib.rcParams['ps.fonttype'] = 42
            # 尝试使用通用字体
            try:
                matplotlib.font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
            except:
                pass

            # 处理ROC数据
            if source_type == 'roc':
                if 'roc_data' not in inputs or not inputs['roc_data']:
                    return ExecutionResult(
                        success=False,
                        error_message="缺少ROC曲线数据输入"
                    )
                
                roc_data = inputs['roc_data']
                # 使用ROC数据创建折线图
                try:
                    # 准备绘图
                    plt.figure(figsize=(6, 4))
                    
                    # 使用中文字体
                    setup_chinese_font()
                    
                    # 绘制ROC曲线
                    if 'series' in roc_data and roc_data['series']:
                        series = roc_data['series'][0]
                        data_points = series['data']
                        plt.plot([point['x'] for point in data_points], 
                                [point['y'] for point in data_points], 
                                'b-', lw=2, label=f'ROC曲线')
                    elif 'fpr' in roc_data and 'tpr' in roc_data:
                        plt.plot(roc_data['fpr'], roc_data['tpr'], 'b-', lw=2)
                    
                    # 绘制随机猜测线
                    plt.plot([0, 1], [0, 1], 'k--', lw=1)
                    
                    # 获取AUC值
                    auc_value = None
                    if 'auc' in roc_data:
                        if isinstance(roc_data['auc'], list) and roc_data['auc']:
                            auc_value = roc_data['auc'][0]
                        else:
                            auc_value = roc_data['auc']
                    
                    # 设置标题和标签
                    title = parameters.get('title', 'ROC曲线')
                    if auc_value is not None:
                        plt.title(f"{title} (AUC = {auc_value:.4f})")
                    else:
                        plt.title(title)
                    
                    plt.xlabel('假阳性率 (False Positive Rate)')
                    plt.ylabel('真阳性率 (True Positive Rate)')
                    plt.grid(True)
                    
                    # 保存为图片，添加图像压缩
                    img_data = self._fig_to_base64(plt)
                    plt.close()
                    
                    # 限制图像大小，防止数据库保存失败
                    if len(img_data) > 500000:  # 约500KB
                        # 进一步压缩图像
                        img_data_compressed = self._compress_image_data(img_data, target_size=500000)
                        # 检查是否压缩成功
                        if img_data_compressed:
                            img_data = img_data_compressed
                            logs.append("图像已压缩以适应数据库存储限制")
                    
                    # 构建输出
                    result = {
                        'chart': img_data,
                        'chart_type': 'line',
                        'title': title,
                        'auc': auc_value
                    }
                    
                    return ExecutionResult(
                        success=True,
                        outputs=result,
                        logs=["ROC曲线绘制成功"]
                    )
                    
                except Exception as e:
                    logger.error(f"绘制ROC曲线时出错: {str(e)}")
                    logger.error(traceback.format_exc())
                    return ExecutionResult(
                        success=False,
                        error_message=f"绘制ROC曲线失败: {str(e)}",
                        logs=[traceback.format_exc()]
                    )
            
            else:
                # 处理标准数据集
                if 'dataset' not in inputs:
                    return ExecutionResult(
                        success=False,
                        error_message="缺少输入数据集",
                        logs=["请连接数据集"]
                    )
                
                dataset = inputs['dataset']
                x_column = parameters.get('x_column', '')
                y_columns = parameters.get('y_columns', '')
                
                if isinstance(y_columns, str):
                    y_columns = [col.strip() for col in y_columns.split(',') if col.strip()]
                
                if not x_column or not y_columns:
                    return ExecutionResult(
                        success=False,
                        error_message="必须指定X轴和至少一个Y轴列",
                        logs=["请指定X轴和Y轴列"]
                    )
                
                # 转换为Python代码
                code = f"""
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    import seaborn as sns
    import io
    import base64
    
    # 设置中文支持
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 额外的字体处理
    import matplotlib
    matplotlib.rcParams['pdf.fonttype'] = 42
    matplotlib.rcParams['ps.fonttype'] = 42
    
    # 尝试加载系统中的字体
    try:
        import os
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf", 
            "/usr/share/fonts/TTF/DejaVuSans.ttf"
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                matplotlib.font_manager.fontManager.addfont(font_path)
    except Exception as e:
        print(f"字体加载警告: {e}")
    
    # 刷新字体缓存
    try:
        matplotlib.font_manager._load_fontmanager(try_read_cache=False)
    except:
        pass
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 处理列名参数
    x_column = '{x_column}'
    y_columns = {y_columns}
    
    # 检查列是否存在
    if x_column not in df.columns:
        raise ValueError(f"找不到X轴列: {{x_column}}")
    
    missing_columns = [col for col in y_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"找不到Y轴列: {{', '.join(missing_columns)}}")
    
    # 创建图形
    plt.figure(figsize=(12, 6))
    
    # 绘制每一个Y轴列
    for y_column in y_columns:
        if pd.api.types.is_numeric_dtype(df[y_column]):
            if {show_markers}:
                plt.plot(df[x_column], df[y_column], marker='o', label=y_column)
            else:
                plt.plot(df[x_column], df[y_column], label=y_column)
    
    # 设置标题和标签
    plt.title('{title}')
    plt.xlabel(x_column)
    plt.ylabel(', '.join(y_columns))
    plt.legend()
    
    # 如果x轴标签太多，旋转它们
    if len(df[x_column].unique()) > 10:
        plt.xticks(rotation=45, ha='right')
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # 保存图像为base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # 返回结果
    result = {{
        'chart_type': 'line',
        'title': '{title}',
        'image': img_str,
        'x_column': x_column,
        'y_columns': y_columns
    }}
except Exception as e:
    raise Exception(f"生成折线图失败: {{str(e)}}")
"""
                
                # 在容器中执行
                exec_result = self.execute_in_container(code)
                
                if exec_result.get('success', False):
                    result = exec_result.get('result', {})
                    return ExecutionResult(
                        success=True,
                        outputs=result,
                        logs=["折线图生成完成"]
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        error_message=exec_result.get('error', '生成折线图失败'),
                        logs=[exec_result.get('traceback', '')]
                    )
                
        except Exception as e:
            logger.error(f"执行折线图生成器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class HeatmapGenerator(BaseComponentExecutor):
    """热力图生成器
    
    生成热力图，用于展示变量之间的相关性、数据矩阵或混淆矩阵。
    对应前端组件ID: heatmap
    """
    
    def _fig_to_base64(self, plt, dpi=100, quality=90):
        """将matplotlib图形转换为base64编码的字符串
        
        Args:
            plt: matplotlib pyplot对象
            dpi: 图像DPI（每英寸点数），影响图像质量和大小
            quality: JPEG压缩质量（仅当format='jpg'时使用）
            
        Returns:
            str: 图像的base64编码字符串
        """
        
        import io
        import base64
        
        # 确保图形尺寸合适，避免模态框内需要滚动条
        figsize = plt.gcf().get_size_inches()
        if figsize[0] > 12 or figsize[1] > 8:
            # 重新设置图形尺寸，保持原比例但最大化在12x8范围内
            scale = min(12/figsize[0], 8/figsize[1])
            new_figsize = (figsize[0] * scale, figsize[1] * scale)
            plt.gcf().set_size_inches(new_figsize)
        
        # 保存图像为base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        return img_str
        
    def _compress_image_data(self, base64_str, target_size=500000):
        """压缩base64编码的图像数据
        
        Args:
            base64_str: 原始base64编码字符串
            target_size: 目标大小（字节数）
            
        Returns:
            str: 压缩后的base64编码字符串，如果失败则返回None
        """
        try:
            import base64
            import io
            from PIL import Image
            
            # 解码base64字符串
            img_data = base64.b64decode(base64_str)
            img_buf = io.BytesIO(img_data)
            img = Image.open(img_buf)
            
            # 计算当前大小
            current_size = len(base64_str)
            
            # 如果已经小于目标大小，直接返回
            if current_size <= target_size:
                return base64_str
                
            # 确定压缩质量和尺寸缩放因子
            quality = 85
            scale_factor = 1.0
            
            # 尝试不同的压缩参数，直到满足大小要求
            for attempt in range(5):  # 最多尝试5次
                # 缩放图像
                if scale_factor < 1.0:
                    new_width = int(img.width * scale_factor)
                    new_height = int(img.height * scale_factor)
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                else:
                    resized_img = img
                
                # 保存为JPEG格式（有损压缩）
                output_buf = io.BytesIO()
                resized_img.convert('RGB').save(output_buf, format='JPEG', quality=quality)
                output_buf.seek(0)
                
                # 编码为base64
                compressed_data = base64.b64encode(output_buf.getvalue()).decode('utf-8')
                
                # 检查是否达到目标大小
                if len(compressed_data) <= target_size:
                    return compressed_data
                
                # 调整参数用于下一次尝试
                if quality > 40:
                    quality -= 10  # 降低质量
                else:
                    scale_factor *= 0.8  # 缩小图像
            
            # 最后尝试：极端压缩
            output_buf = io.BytesIO()
            img.resize((img.width // 2, img.height // 2), Image.LANCZOS).convert('RGB').save(
                output_buf, format='JPEG', quality=30)
            output_buf.seek(0)
            return base64.b64encode(output_buf.getvalue()).decode('utf-8')
            
        except Exception as e:
            logger.warning(f"压缩图像失败: {str(e)}")
            return None
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成热力图
        
        Args:
            inputs: 输入数据，包括:
                - data: 输入数据集
                - confusion_matrix: 混淆矩阵数据（来自ConfusionMatrixGenerator）
            parameters: 参数，包括:
                - columns: 要绘制的列（可选，逗号分隔）
                - computation: 计算方法（correlation、covariance）
                - title: 图表标题
                - cmap: 颜色映射
                - cluster: 是否聚类
                
        Returns:
            ExecutionResult: 执行结果，包含生成的热力图
        """
        try:
            # 获取输入数据
            if 'confusion_matrix' in inputs:
                # 使用混淆矩阵数据
                confusion_matrix_data = inputs['confusion_matrix']
                
                # 直接使用混淆矩阵数据绘制热力图
                return self._generate_confusion_heatmap(confusion_matrix_data, parameters)
                
            elif 'data' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['data']
            
            # 获取参数
            columns = parameters.get('columns', '')
            computation = parameters.get('computation', 'correlation')
            title = parameters.get('title', '热力图')
            cmap = parameters.get('cmap', 'viridis')
            cluster = parameters.get('cluster', False)
            
            # 兼容不同的布尔值表示方式
            if isinstance(cluster, str):
                cluster = cluster.lower() == 'true'
            
            # 处理列参数
            if isinstance(columns, str) and columns:
                columns = [col.strip() for col in columns.split(',') if col.strip()]
            else:
                columns = []
            
            # 直接在Python中执行
            code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from scipy.cluster import hierarchy
from scipy.spatial import distance

# 应用中文字体设置
try:
    setup_chinese_font()
except Exception as e:
    logger.warning(f"设置中文字体失败: {str(e)}")
    # 基本字体设置，确保有备选方案
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

# 加载数据
if isinstance(dataset, dict) and 'data' in dataset:
    if isinstance(dataset['data'], str):
        data = pd.read_json(dataset['data'], orient='split')
    else:
        data = pd.DataFrame(dataset['data'])
else:
    data = pd.DataFrame(dataset)

# 检查列是否存在
if columns:
    # 检查所有指定的列是否存在
    missing_cols = [col for col in columns if col not in data.columns]
    if missing_cols:
        return ExecutionResult(
            success=False,
            error_message=f"以下列不存在于数据集中: {', '.join(missing_cols)}"
        )
    
    # 只使用选定的列
    data = data[columns]

# 检查是否有数值列
numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
if not numeric_cols:
    return ExecutionResult(
        success=False,
        error_message="没有数值列可以用于生成热力图"
    )

# 如果指定的列中有非数值列，则过滤掉
if columns:
    non_numeric = [col for col in columns if col not in numeric_cols]
    if non_numeric:
        return ExecutionResult(
            success=False,
            error_message=f"以下列不是数值类型: {', '.join(non_numeric)}"
        )
else:
    # 如果没有指定列，则使用所有数值列
    data = data[numeric_cols]

# 计算相关矩阵或协方差矩阵
if computation == 'correlation':
    matrix = data.corr()
elif computation == 'covariance':
    matrix = data.cov()
else:
    return ExecutionResult(
        success=False,
        error_message=f"不支持的计算方法: {computation}"
    )

# 创建图形
plt.figure(figsize=(10, 8))

# 处理聚类
if cluster and len(matrix) > 1:
    # 计算距离矩阵
    correlations_array = np.asarray(matrix)
    row_linkage = hierarchy.linkage(distance.pdist(correlations_array), method='average')
    col_linkage = hierarchy.linkage(distance.pdist(correlations_array.T), method='average')

    # 创建聚类热力图
    g = sns.clustermap(
        matrix, 
        figsize=(10, 8),
        cmap=cmap,
        row_linkage=row_linkage,
        col_linkage=col_linkage
    )
    # 获取最后创建的图像
    fig = plt.gcf()
    plt.title(title)
else:
    # 创建普通热力图
    sns.heatmap(
        matrix, 
        annot=True, 
        cmap=cmap, 
        linewidths=.5, 
        fmt=".2f",
        square=True
    )
    plt.title(title)

# 保存为图片
img_data = fig_to_base64(plt)

# 构建输出结果
result = {
    'chart_type': 'heatmap',
    'title': title,
    'image': img_data,
    'computation': computation
}
"""
            
            # 创建一个本地变量字典，包含必要的变量
            local_vars = {
                'dataset': dataset,
                'columns': columns,
                'computation': computation,
                'title': title,
                'cmap': cmap,
                'cluster': cluster,
                'logger': logger,
                'setup_chinese_font': setup_chinese_font,
                'ExecutionResult': ExecutionResult,
                'fig_to_base64': self._fig_to_base64
            }
            
            # 执行代码
            try:
                exec(code, globals(), local_vars)
                result = local_vars.get('result', {})
                
                return ExecutionResult(
                    success=True,
                    outputs=result,
                    logs=[f"热力图生成成功: {computation} 方法"]
                )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error_message=f"生成热力图失败: {str(e)}",
                    logs=[traceback.format_exc()]
                )
        except Exception as e:
            logger.error(f"执行热力图生成器时出错: {str(e)}")
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
            
    def _generate_confusion_heatmap(self, confusion_matrix_data: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """生成基于混淆矩阵数据的热力图
        
        Args:
            confusion_matrix_data: 混淆矩阵数据
            parameters: 图表参数
            
        Returns:
            ExecutionResult: 执行结果
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            import numpy as np
            
            # 获取参数
            title = parameters.get('title', '混淆矩阵')
            cmap = parameters.get('cmap', 'Blues')
            
            # 应用中文字体设置
            try:
                setup_chinese_font()
            except Exception as e:
                logger.warning(f"设置中文字体失败: {str(e)}")
                # 基本字体设置，确保有备选方案
                plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
            
            # 提取混淆矩阵数据
            if 'confusion_matrix' not in confusion_matrix_data:
                return ExecutionResult(
                    success=False,
                    error_message="输入数据缺少混淆矩阵信息"
                )
            
            cm_data = confusion_matrix_data['confusion_matrix']
            heatmap_data = cm_data.get('data', [])
            x_labels = cm_data.get('x_labels', [])
            y_labels = cm_data.get('y_labels', [])
            normalized = cm_data.get('normalized', False)
            
            # 将热力图数据转换为矩阵形式
            # 确定矩阵大小
            max_x = max([item.get('x', 0) for item in heatmap_data]) + 1 if heatmap_data else 0
            max_y = max([item.get('y', 0) for item in heatmap_data]) + 1 if heatmap_data else 0
            
            # 创建矩阵并填充数据
            matrix = np.zeros((max_y, max_x))
            for item in heatmap_data:
                x = item.get('x', 0)
                y = item.get('y', 0)
                value = item.get('value', 0)
                matrix[y, x] = value
            
            # 创建热力图
            plt.figure(figsize=(6, 4))
            
            # 修复格式化问题：无论是否归一化，都使用浮点数格式
            # 对于归一化的值使用2位小数，对于原始值使用带有整数的格式
            fmt = '.2f' if normalized else '.0f'
            
            ax = sns.heatmap(
                matrix,
                annot=True,
                cmap=cmap,
                fmt=fmt,
                cbar=True,
                square=True,
                xticklabels=x_labels,
                yticklabels=y_labels
            )
            
            # 设置标题和标签
            plt.title(title)
            plt.xlabel('预测值')
            plt.ylabel('真实值')
            
            # 调整标签位置
            plt.tight_layout()
            
            # 将图形转换为base64编码的图像，使用较低的DPI以减小大小
            img_data = self._fig_to_base64(plt, dpi=90)
            
            # 限制图像大小，防止数据库保存失败
            if len(img_data) > 500000:  # 约500KB
                # 进一步压缩图像
                img_data_compressed = self._compress_image_data(img_data, target_size=500000)
                # 检查是否压缩成功
                if img_data_compressed:
                    img_data = img_data_compressed
                    logger.info("混淆矩阵图像已压缩以适应数据库存储限制")
            
            # 从输入中提取准确率
            accuracy = None
            if 'accuracy' in confusion_matrix_data:
                accuracy = confusion_matrix_data['accuracy']
            
            # 构建输出结果
            result = {
                'chart_type': 'heatmap',
                'title': title,
                'image': img_data,
                'computation': 'confusion_matrix',
                'accuracy': accuracy  # 添加准确率
            }
            
            return ExecutionResult(
                success=True,
                outputs=result,
                logs=["混淆矩阵热力图生成成功"]
            )
        except Exception as e:
            logger.error(f"生成混淆矩阵热力图失败: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=f"生成混淆矩阵热力图失败: {str(e)}",
                logs=[traceback.format_exc()]
            )


