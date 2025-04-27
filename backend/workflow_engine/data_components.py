"""
数据输入和预处理组件执行器

该模块实现了数据输入和预处理相关的组件执行器，如数据加载、清洗、转换和特征工程等。
"""

import logging
import json
import traceback
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .executors import BaseComponentExecutor, ExecutionResult

logger = logging.getLogger(__name__)

class CSVDataLoader(BaseComponentExecutor):
    """CSV数据加载器
    
    加载CSV格式的数据文件，并转换为数据集对象。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        加载CSV数据文件
        
        Args:
            inputs: 输入数据
            parameters: 参数，包括:
                - file_path: 文件路径（相对于工作区）
                - delimiter: 分隔符
                - header: 是否有标题行
                - index_col: 索引列
                
        Returns:
            ExecutionResult: 执行结果，包含加载的数据集
        """
        try:
            # 获取参数
            file_path = parameters.get('file_path', '')
            delimiter = parameters.get('delimiter', ',')
            header = parameters.get('header', 'true') == 'true'
            index_col = parameters.get('index_col', None)
            
            if not file_path:
                return ExecutionResult(
                    success=False,
                    error_message="未指定文件路径"
                )
            
            # 转换为Python代码
            code = f"""
try:
    # 加载CSV文件
    df = pd.read_csv('/workspace/{file_path}', 
                     delimiter='{delimiter}', 
                     header={0 if header else None}, 
                     index_col={index_col if index_col else None})
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
except Exception as e:
    raise Exception(f"加载CSV文件失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': data_result
                    },
                    logs=["成功加载CSV数据"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '加载CSV文件失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行CSV数据加载器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class ExcelDataLoader(BaseComponentExecutor):
    """Excel数据加载器
    
    加载Excel格式的数据文件，并转换为数据集对象。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        加载Excel数据文件
        
        Args:
            inputs: 输入数据
            parameters: 参数，包括:
                - file_path: 文件路径（相对于工作区）
                - sheet_name: 工作表名称
                - header: 是否有标题行
                
        Returns:
            ExecutionResult: 执行结果，包含加载的数据集
        """
        try:
            # 获取参数
            file_path = parameters.get('file_path', '')
            sheet_name = parameters.get('sheet_name', 0)
            header = parameters.get('header', 'true') == 'true'
            
            if not file_path:
                return ExecutionResult(
                    success=False,
                    error_message="未指定文件路径"
                )
            
            # 转换为Python代码
            code = f"""
try:
    # 加载Excel文件
    df = pd.read_excel('/workspace/{file_path}', 
                      sheet_name={repr(sheet_name)}, 
                      header={0 if header else None})
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
except Exception as e:
    raise Exception(f"加载Excel文件失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': data_result
                    },
                    logs=["成功加载Excel数据"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '加载Excel文件失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行Excel数据加载器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class JSONDataLoader(BaseComponentExecutor):
    """JSON数据加载器
    
    加载JSON格式的数据文件，并转换为数据集对象。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        加载JSON数据文件
        
        Args:
            inputs: 输入数据
            parameters: 参数，包括:
                - file_path: 文件路径（相对于工作区）
                - orient: JSON格式（records, split, index等）
                
        Returns:
            ExecutionResult: 执行结果，包含加载的数据集
        """
        try:
            # 获取参数
            file_path = parameters.get('file_path', '')
            orient = parameters.get('orient', 'records')
            
            if not file_path:
                return ExecutionResult(
                    success=False,
                    error_message="未指定文件路径"
                )
            
            # 转换为Python代码
            code = f"""
try:
    # 加载JSON文件
    df = pd.read_json('/workspace/{file_path}', orient='{orient}')
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
except Exception as e:
    raise Exception(f"加载JSON文件失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': data_result
                    },
                    logs=["成功加载JSON数据"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '加载JSON文件失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行JSON数据加载器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class RandomDataGenerator(BaseComponentExecutor):
    """随机数据生成器
    
    生成随机数据集，用于测试和原型设计。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成随机数据集
        
        Args:
            inputs: 输入数据
            parameters: 参数，包括:
                - rows: 行数
                - columns: 列数
                - column_type: 数据类型（数值、分类等）
                
        Returns:
            ExecutionResult: 执行结果，包含生成的数据集
        """
        try:
            # 获取参数
            rows = int(parameters.get('rows', 100))
            columns = int(parameters.get('columns', 5))
            column_type = parameters.get('column_type', 'numeric')
            include_target = parameters.get('include_target', 'true') == 'true'
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    
    # 生成随机数据
    np.random.seed(42)  # 固定随机种子
    
    if '{column_type}' == 'numeric':
        # 生成数值型数据
        data = np.random.randn({rows}, {columns})
        columns = [f'feature_{{i+1}}' for i in range({columns})]
        df = pd.DataFrame(data, columns=columns)
        
        # 如果需要目标变量
        if {include_target}:
            # 生成连续型目标变量
            df['target'] = df.sum(axis=1) + np.random.randn({rows}) * 0.5
    
    elif '{column_type}' == 'categorical':
        # 生成分类型数据
        categories = ['A', 'B', 'C', 'D', 'E']
        data = np.random.choice(categories, size=({rows}, {columns}))
        columns = [f'cat_feature_{{i+1}}' for i in range({columns})]
        df = pd.DataFrame(data, columns=columns)
        
        # 如果需要目标变量
        if {include_target}:
            # 生成分类型目标变量
            df['target'] = np.random.choice(['Class1', 'Class2', 'Class3'], size={rows})
    
    elif '{column_type}' == 'mixed':
        # 生成混合型数据
        df = pd.DataFrame()
        
        # 数值型列
        for i in range({columns} // 2):
            df[f'num_feature_{{i+1}}'] = np.random.randn({rows})
        
        # 分类型列
        categories = ['A', 'B', 'C', 'D', 'E']
        for i in range({columns} // 2, {columns}):
            df[f'cat_feature_{{i+1}}'] = np.random.choice(categories, size={rows})
        
        # 如果需要目标变量
        if {include_target}:
            # 随机选择连续型或分类型目标
            if np.random.random() > 0.5:
                df['target'] = df.select_dtypes(include='number').sum(axis=1) + np.random.randn({rows}) * 0.5
            else:
                df['target'] = np.random.choice(['Class1', 'Class2', 'Class3'], size={rows})
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
except Exception as e:
    raise Exception(f"生成随机数据失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': data_result
                    },
                    logs=[f"成功生成随机数据集: {rows}行 x {columns}列"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '生成随机数据失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行随机数据生成器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class DataCleaner(BaseComponentExecutor):
    """数据清洗器
    
    清洗数据集中的缺失值、异常值等。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        清洗数据集
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
            parameters: 参数，包括:
                - handle_missing: 缺失值处理方式（删除、填充等）
                - handle_outliers: 是否处理异常值
                - columns: 要处理的列
                
        Returns:
            ExecutionResult: 执行结果，包含清洗后的数据集
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
            handle_missing = parameters.get('handle_missing', 'drop')
            fill_value = parameters.get('fill_value', '')
            handle_outliers = parameters.get('handle_outliers', 'false') == 'true'
            columns = parameters.get('columns', [])
            if columns and isinstance(columns, str):
                columns = columns.split(',')
            
            # 转换为Python代码
            code = f"""
try:
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 选择要处理的列
    columns_to_process = {repr(columns)} if {repr(columns)} else df.columns.tolist()
    
    # 处理缺失值
    if '{handle_missing}' == 'drop':
        # 删除缺失值
        df = df.dropna(subset=columns_to_process)
    elif '{handle_missing}' == 'fill_mean':
        # 用均值填充数值型列的缺失值
        for col in columns_to_process:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].mean())
    elif '{handle_missing}' == 'fill_median':
        # 用中位数填充数值型列的缺失值
        for col in columns_to_process:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].median())
    elif '{handle_missing}' == 'fill_mode':
        # 用众数填充缺失值
        for col in columns_to_process:
            df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else None)
    elif '{handle_missing}' == 'fill_value':
        # 用指定值填充缺失值
        fill_value = '{fill_value}'
        for col in columns_to_process:
            # 根据列类型转换填充值
            if pd.api.types.is_numeric_dtype(df[col]):
                try:
                    val = float(fill_value)
                except:
                    val = 0
                df[col] = df[col].fillna(val)
            else:
                df[col] = df[col].fillna(fill_value)
    
    # 处理异常值
    if {handle_outliers}:
        for col in columns_to_process:
            if pd.api.types.is_numeric_dtype(df[col]):
                # 使用IQR方法检测和处理异常值
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # 异常值替换为边界值
                df[col] = df[col].apply(lambda x: lower_bound if x < lower_bound else (upper_bound if x > upper_bound else x))
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records'),
        'cleaned_records': len(df)
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
except Exception as e:
    raise Exception(f"清洗数据失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': data_result
                    },
                    logs=["数据清洗完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '数据清洗失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行数据清洗器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
