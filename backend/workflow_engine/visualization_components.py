"""
可视化组件执行器

该模块实现了数据可视化相关的组件执行器，用于生成各种图表和可视化结果。
"""

import logging
import json
import traceback
from typing import Dict, Any, List
from .executors import BaseComponentExecutor, ExecutionResult

logger = logging.getLogger(__name__)

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
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 处理列名参数
    x_column = '{x_column}'
    y_column = '{y_column}'
    
    # 如果没有指定y_column，则进行频次统计
    if not y_column:
        if x_column not in df.columns:
            raise ValueError(f"找不到列: {{x_column}}")
        # 获取分类频次
        counts = df[x_column].value_counts().reset_index()
        counts.columns = ['category', 'count']
        x_data = counts['category']
        y_data = counts['count']
        if '{orientation}' == 'vertical':
            plt.figure(figsize=(10, 6))
            plt.bar(x_data, y_data, color='{color}')
            plt.xlabel(x_column)
            plt.ylabel('频次')
        else:
            plt.figure(figsize=(8, len(x_data) * 0.5 + 2))
            plt.barh(x_data, y_data, color='{color}')
            plt.xlabel('频次')
            plt.ylabel(x_column)
    
    # 如果同时指定了x_column和y_column
    elif x_column and y_column:
        if x_column not in df.columns or y_column not in df.columns:
            raise ValueError(f"找不到列: {{x_column if x_column not in df.columns else y_column}}")
        
        # 如果y_column是数值类型，直接绘制
        if pd.api.types.is_numeric_dtype(df[y_column]):
            if '{orientation}' == 'vertical':
                plt.figure(figsize=(12, 6))
                plt.bar(df[x_column], df[y_column], color='{color}')
                plt.xlabel(x_column)
                plt.ylabel(y_column)
                # 如果x轴标签太多，旋转它们
                if len(df[x_column].unique()) > 10:
                    plt.xticks(rotation=45, ha='right')
            else:
                plt.figure(figsize=(8, len(df[x_column].unique()) * 0.5 + 2))
                plt.barh(df[x_column], df[y_column], color='{color}')
                plt.xlabel(y_column)
                plt.ylabel(x_column)
        # 如果y_column不是数值类型，做分组统计
        else:
            # 获取交叉表
            cross_tab = pd.crosstab(df[x_column], df[y_column])
            if '{orientation}' == 'vertical':
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
    
    plt.title('{title}')
    plt.tight_layout()
    
    # 保存图像为base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # 返回结果
    result = {{
        'chart_type': 'bar',
        'title': '{title}',
        'image': img_str,
        'x_column': x_column,
        'y_column': y_column
    }}
except Exception as e:
    raise Exception(f"生成柱状图失败: {{str(e)}}")
"""
            
            # 在容器中执行
            exec_result = self.execute_in_container(code)
            
            if exec_result.get('success', False):
                result = exec_result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs=result,
                    logs=["柱状图生成完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=exec_result.get('error', '生成柱状图失败'),
                    logs=[exec_result.get('traceback', '')]
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
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成折线图
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
            parameters: 参数，包括:
                - x_column: X轴列名
                - y_columns: Y轴列名（可以是多个，用逗号分隔）
                - title: 图表标题
                - show_markers: 是否显示标记点
                
        Returns:
            ExecutionResult: 执行结果，包含生成的折线图
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
            y_columns = parameters.get('y_columns', '')
            if isinstance(y_columns, str):
                y_columns = [col.strip() for col in y_columns.split(',') if col.strip()]
            
            title = parameters.get('title', '折线图')
            show_markers = parameters.get('show_markers', 'true') == 'true'
            
            if not x_column or not y_columns:
                return ExecutionResult(
                    success=False,
                    error_message="必须指定X轴和至少一个Y轴列"
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
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    
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


class ScatterPlotGenerator(BaseComponentExecutor):
    """散点图生成器
    
    生成散点图，展示两个数值变量之间的关系。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成散点图
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
            parameters: 参数，包括:
                - x_column: X轴列名
                - y_column: Y轴列名
                - color_column: 着色列（可选）
                - title: 图表标题
                - show_regression: 是否显示回归线
                
        Returns:
            ExecutionResult: 执行结果，包含生成的散点图
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
            color_column = parameters.get('color_column', '')
            title = parameters.get('title', '散点图')
            show_regression = parameters.get('show_regression', 'true') == 'true'
            
            if not x_column or not y_column:
                return ExecutionResult(
                    success=False,
                    error_message="必须指定X轴和Y轴列"
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
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 处理列名参数
    x_column = '{x_column}'
    y_column = '{y_column}'
    color_column = '{color_column}'
    
    # 检查列是否存在
    if x_column not in df.columns or y_column not in df.columns:
        raise ValueError(f"找不到列: {{x_column if x_column not in df.columns else y_column}}")
    
    if color_column and color_column not in df.columns:
        raise ValueError(f"找不到颜色列: {{color_column}}")
    
    # 检查列类型
    if not pd.api.types.is_numeric_dtype(df[x_column]) or not pd.api.types.is_numeric_dtype(df[y_column]):
        raise ValueError(f"X轴和Y轴列必须是数值类型")
    
    # 创建图形
    plt.figure(figsize=(10, 6))
    
    # 绘制散点图
    if color_column:
        scatter = plt.scatter(df[x_column], df[y_column], c=df[color_column] if pd.api.types.is_numeric_dtype(df[color_column]) else None, 
                            alpha=0.6, cmap='viridis')
        
        # 如果颜色列是分类变量，添加图例
        if not pd.api.types.is_numeric_dtype(df[color_column]):
            # 获取唯一分类
            categories = df[color_column].unique()
            for category in categories:
                mask = df[color_column] == category
                plt.scatter(df.loc[mask, x_column], df.loc[mask, y_column], alpha=0.6, label=category)
            plt.legend(title=color_column)
        else:
            # 添加颜色条
            plt.colorbar(scatter, label=color_column)
    else:
        plt.scatter(df[x_column], df[y_column], alpha=0.6)
    
    # 添加回归线
    if {show_regression}:
        if not color_column or pd.api.types.is_numeric_dtype(df[color_column]):
            # 简单线性回归
            z = np.polyfit(df[x_column], df[y_column], 1)
            p = np.poly1d(z)
            plt.plot(df[x_column], p(df[x_column]), "r--", alpha=0.8, label=f"y = {{z[0]:.2f}}x + {{z[1]:.2f}}")
            plt.legend()
        else:
            # 对每个分类绘制回归线
            categories = df[color_column].unique()
            for category in categories:
                mask = df[color_column] == category
                if sum(mask) > 1:  # 至少需要两个点才能拟合回归线
                    z = np.polyfit(df.loc[mask, x_column], df.loc[mask, y_column], 1)
                    p = np.poly1d(z)
                    plt.plot(df.loc[mask, x_column], p(df.loc[mask, x_column]), "--", alpha=0.8)
    
    # 设置标题和标签
    plt.title('{title}')
    plt.xlabel(x_column)
    plt.ylabel(y_column)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # 保存图像为base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # 计算相关系数
    corr = df[[x_column, y_column]].corr().iloc[0, 1]
    
    # 返回结果
    result = {{
        'chart_type': 'scatter',
        'title': '{title}',
        'image': img_str,
        'x_column': x_column,
        'y_column': y_column,
        'color_column': color_column if color_column else None,
        'correlation': float(corr)
    }}
except Exception as e:
    raise Exception(f"生成散点图失败: {{str(e)}}")
"""
            
            # 在容器中执行
            exec_result = self.execute_in_container(code)
            
            if exec_result.get('success', False):
                result = exec_result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs=result,
                    logs=["散点图生成完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=exec_result.get('error', '生成散点图失败'),
                    logs=[exec_result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行散点图生成器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class HistogramGenerator(BaseComponentExecutor):
    """直方图生成器
    
    生成直方图，用于展示数值数据的分布。
    对应前端组件ID: histogram
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成直方图
        
        Args:
            inputs: 输入数据，包括:
                - data: 输入数据集
            parameters: 参数，包括:
                - column: 要绘制的列
                - bins: 分箱数
                - title: 图表标题
                - xlabel: X轴标签
                - ylabel: Y轴标签
                - color: 颜色
                - kde: 是否显示核密度估计
                
        Returns:
            ExecutionResult: 执行结果，包含生成的直方图
        """
        try:
            # 获取输入数据
            if 'data' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['data']
            
            # 获取参数
            column = parameters.get('column', '')
            bins = parameters.get('bins', 20)
            title = parameters.get('title', '直方图')
            xlabel = parameters.get('xlabel', '')
            ylabel = parameters.get('ylabel', '频率')
            color = parameters.get('color', '#9c27b0')
            kde = parameters.get('kde', False)
            
            # 检查参数
            if not column:
                return ExecutionResult(
                    success=False,
                    error_message="需要指定要绘制的列"
                )
            
            # 生成Python代码
            code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import json

# 加载数据
data = pd.read_json(r'''{}''')

# 获取参数
column = '{}'
bins = {}
title = '{}'
xlabel = '{}'
ylabel = '{}'
color = '{}'
kde = {}

# 检查列是否存在
if column not in data.columns:
    raise ValueError(f"列 {column} 不存在于数据集中")

# 设置样式
sns.set_style('whitegrid')
plt.figure(figsize=(10, 6))

# 绘制直方图
if kde:
    # 使用seaborn绘制KDE曲线
    ax = sns.histplot(data[column], bins=bins, kde=True, color=color)
else:
    # 使用matplotlib绘制普通直方图
    ax = plt.hist(data[column], bins=bins, color=color, alpha=0.7, edgecolor='black')
    
# 设置标题和标签
plt.title(title, fontsize=15)
plt.xlabel(xlabel if xlabel else column, fontsize=12)
plt.ylabel(ylabel, fontsize=12)
plt.grid(True, alpha=0.3)

# 添加数据统计信息
mean_val = data[column].mean()
median_val = data[column].median()
std_val = data[column].std()

stats_text = f"均值: {mean_val:.2f}\\n中位数: {median_val:.2f}\\n标准差: {std_val:.2f}"
plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
             fontsize=10, bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8),
             ha='right', va='top')

# 将图表转换为base64编码的图像
buf = io.BytesIO()
plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
buf.seek(0)
img_base64 = base64.b64encode(buf.read()).decode('utf-8')
plt.close()

# 准备统计信息
statistics = {{
    'mean': float(mean_val),
    'median': float(median_val),
    'std': float(std_val),
    'min': float(data[column].min()),
    'max': float(data[column].max()),
    'count': int(data[column].count())
}}

# 准备结果
result = {{
    'image': img_base64,
    'statistics': statistics
}}

# 输出结果
print(json.dumps(result))
""".format(json.dumps(dataset), column, bins, title, xlabel, ylabel, color, str(kde).lower())
            
            # 执行代码并获取结果
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"直方图生成失败: {output}"
                )
                
            # 解析输出
            result = json.loads(output)
            
            return ExecutionResult(
                success=True,
                output={
                    'chart': result['image'],
                    'statistics': result['statistics']
                }
            )
            
        except Exception as e:
            error_message = f"生成直方图时出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )


class HeatmapGenerator(BaseComponentExecutor):
    """热力图生成器
    
    生成热力图，用于展示变量之间的相关性或数据矩阵。
    对应前端组件ID: heatmap
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成热力图
        
        Args:
            inputs: 输入数据，包括:
                - data: 输入数据集
            parameters: 参数，包括:
                - columns: 要包含的列（为空则使用所有数值列）
                - computation: 计算方式（correlation, covariance, raw）
                - title: 图表标题
                - cmap: 颜色映射
                - show_values: 是否显示数值
                - cluster: 是否聚类排序
                
        Returns:
            ExecutionResult: 执行结果，包含生成的热力图
        """
        try:
            # 获取输入数据
            if 'data' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['data']
            
            # 获取参数
            columns = parameters.get('columns', '')
            computation = parameters.get('computation', 'correlation')
            title = parameters.get('title', '热力图')
            cmap = parameters.get('cmap', 'coolwarm')
            show_values = parameters.get('show_values', True)
            cluster = parameters.get('cluster', False)
            
            # 处理列参数
            if isinstance(columns, str) and columns:
                columns = [col.strip() for col in columns.split(',') if col.strip()]
            else:
                columns = []
            
            # 生成Python代码
            code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import json
from scipy.cluster import hierarchy
from scipy.spatial import distance

# 加载数据
data = pd.read_json(r'''{}''')

# 获取参数
columns = {}
computation = '{}'
title = '{}'
cmap = '{}'
show_values = {}
cluster = {}

# 处理列选择
if not columns:
    # 如果没有指定列，使用所有数值列
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    columns = numeric_cols
else:
    # 检查所有指定的列是否存在
    missing_cols = [col for col in columns if col not in data.columns]
    if missing_cols:
        raise ValueError(f"以下列不存在于数据集中: {{missing_cols}}")
    
    # 只保留数值列
    non_numeric = [col for col in columns if col not in data.select_dtypes(include=[np.number]).columns]
    if non_numeric:
        raise ValueError(f"以下列不是数值类型: {{non_numeric}}")

# 选择要处理的数据
selected_data = data[columns]

# 根据计算方式准备数据
if computation == 'correlation':
    # 计算相关性矩阵
    matrix = selected_data.corr()
    vmin, vmax = -1, 1
    label = '相关系数'
elif computation == 'covariance':
    # 计算协方差矩阵
    matrix = selected_data.cov()
    vmin, vmax = None, None
    label = '协方差'
else:  # raw
    # 使用原始数据
    matrix = selected_data
    vmin, vmax = None, None
    label = '值'

# 如果需要聚类排序
if cluster and computation in ['correlation', 'covariance']:
    # 计算距离矩阵
    if computation == 'correlation':
        # 对于相关性，距离是1-|相关系数|
        distance_matrix = 1 - np.abs(matrix)
    else:
        # 对于协方差，使用标准化的距离
        std_matrix = np.diag(1/np.sqrt(np.diag(matrix)))
        normalized_cov = std_matrix @ matrix @ std_matrix
        distance_matrix = 1 - np.abs(normalized_cov)
    
    # 执行层次聚类
    linkage = hierarchy.linkage(distance.squareform(distance_matrix), method='average')
    dendro = hierarchy.dendrogram(linkage, no_plot=True)
    
    # 重新排序矩阵
    reordered_idx = dendro['leaves']
    reordered_cols = [matrix.columns[i] for i in reordered_idx]
    matrix = matrix.loc[reordered_cols, reordered_cols]

# 创建图表
plt.figure(figsize=(12, 10))

# 调整面板大小，为标题留出空间
plt.subplots_adjust(top=0.9)

# 绘制热力图
ax = sns.heatmap(matrix, annot=show_values, fmt='.2f', cmap=cmap, 
                linewidths=0.5, vmin=vmin, vmax=vmax, square=True, 
                cbar_kws={{'label': label}})

# 设置标题
plt.title(title, fontsize=15, pad=20)

# 设置标签
plt.tight_layout()

# 将图表转换为base64编码的图像
buf = io.BytesIO()
plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
buf.seek(0)
img_base64 = base64.b64encode(buf.read()).decode('utf-8')
plt.close()

# 准备矩阵数据（用于可能的进一步分析）
if isinstance(matrix, pd.DataFrame):
    matrix_data = matrix.to_dict(orient='split')
    columns = matrix.columns.tolist()
    index = matrix.index.tolist()
else:
    matrix_data = matrix.tolist()
    columns = list(range(matrix.shape[1]))
    index = list(range(matrix.shape[0]))

# 准备结果
result = {{
    'image': img_base64,
    'matrix': {{
        'data': matrix_data,
        'columns': columns,
        'index': index,
        'computation': computation
    }}
}}

# 输出结果
print(json.dumps(result))
""".format(json.dumps(dataset), columns, computation, title, cmap, str(show_values).lower(), str(cluster).lower())
            
            # 执行代码并获取结果
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"热力图生成失败: {output}"
                )
                
            # 解析输出
            result = json.loads(output)
            
            return ExecutionResult(
                success=True,
                output={
                    'chart': result['image'],
                    'matrix': result['matrix']
                }
            )
            
        except Exception as e:
            error_message = f"生成热力图时出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )


class PieChartGenerator(BaseComponentExecutor):
    """饼图生成器
    
    生成饼图或环形图，用于展示数据各部分占整体的比例。
    对应前端组件ID: pie-chart
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成饼图
        
        Args:
            inputs: 输入数据，包括:
                - data: 输入数据集
            parameters: 参数，包括:
                - labels_column: 标签列
                - values_column: 数值列
                - title: 图表标题
                - donut: 是否为环形图
                - show_pct: 是否显示百分比
                - start_angle: 起始角度
                
        Returns:
            ExecutionResult: 执行结果，包含生成的饼图
        """
        try:
            # 获取输入数据
            if 'data' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['data']
            
            # 获取参数
            labels_column = parameters.get('labels_column', '')
            values_column = parameters.get('values_column', '')
            title = parameters.get('title', '饼图')
            donut = parameters.get('donut', False)
            show_pct = parameters.get('show_pct', True)
            start_angle = parameters.get('start_angle', 0)
            
            # 检查必需参数
            if not labels_column or not values_column:
                return ExecutionResult(
                    success=False,
                    error_message="需要同时指定标签列和数值列"
                )
            
            # 生成Python代码
            code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import json
import matplotlib.colors as mcolors

# 加载数据
data = pd.read_json(r'''{}''')

# 获取参数
labels_column = '{}'
values_column = '{}'
title = '{}'
donut = {}
show_pct = {}
start_angle = {}

# 检查列是否存在
if labels_column not in data.columns:
    raise ValueError(f"标签列 {labels_column} 不存在于数据集中")

if values_column not in data.columns:
    raise ValueError(f"数值列 {values_column} 不存在于数据集中")

# 准备数据
labels = data[labels_column].tolist()
values = data[values_column].tolist()

# 如果值有负数，给出警告并取绝对值
if any(v < 0 for v in values):
    print("Warning: 饼图不能绘制负值，已自动取绝对值")
    values = [abs(v) for v in values]

# 创建饼图
plt.figure(figsize=(10, 8))

# 自动生成颜色
colors = list(mcolors.TABLEAU_COLORS.values())
if len(labels) > len(colors):
    # 如果标签数超过预定义颜色数，则使用随机颜色
    import random
    random.seed(42)  # 使颜色生成可重现
    colors = [mcolors.to_rgb(plt.cm.tab20(i)) for i in range(len(labels))]

# 计算百分比
percentages = [100. * v / sum(values) for v in values]

# 绘制饼图
patches, texts, autotexts = plt.pie(
    values, 
    labels=labels, 
    colors=colors,
    autopct='%1.1f%%' if show_pct else None,
    startangle=start_angle,
    wedgeprops=dict(width=0.3 if donut else 0, edgecolor='w')
)

# 设置百分比文本属性
if show_pct:
    for autotext in autotexts:
        autotext.set_size(9)
        autotext.set_weight('bold')

# 设置标题
plt.title(title, fontsize=15)

# 使绘图区域成为一个圆
plt.axis('equal')

# 添加图例（如果有很多项）
if len(labels) > 7:  # 只有在标签很多时才添加图例
    plt.legend(
        patches, 
        labels, 
        loc='center left',
        bbox_to_anchor=(1, 0.5),
        fontsize=9
    )

# 将图表转换为base64编码的图像
buf = io.BytesIO()
plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
buf.seek(0)
img_base64 = base64.b64encode(buf.read()).decode('utf-8')
plt.close()

# 准备数据摘要
data_summary = [
    {{"label": str(label), "value": float(value), "percentage": float(pct)}}
    for label, value, pct in zip(labels, values, percentages)
]

# 准备结果
result = {{
    'image': img_base64,
    'data': data_summary,
    'total': float(sum(values))
}}

# 输出结果
print(json.dumps(result))
""".format(json.dumps(dataset), labels_column, values_column, title, 
           str(donut).lower(), str(show_pct).lower(), start_angle)
            
            # 执行代码并获取结果
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"饼图生成失败: {output}"
                )
                
            # 解析输出
            result = json.loads(output)
            
            return ExecutionResult(
                success=True,
                output={
                    'chart': result['image'],
                    'data': result['data'],
                    'total': result['total']
                }
            )
            
        except Exception as e:
            error_message = f"生成饼图时出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )
