"""
特征工程组件执行器

该模块实现了与特征工程相关的组件执行器，包括特征选择、特征转换和数据编码等。
"""

import logging
import json
import traceback
import io
from typing import Dict, Any, List
from .executors import BaseComponentExecutor, ExecutionResult

logger = logging.getLogger(__name__)

class FeatureTransformer(BaseComponentExecutor):
    """特征转换器
    
    对数据集的特征进行变换，如对数变换、平方根变换等。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        转换特征
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
            parameters: 参数，包括:
                - transformation: 变换类型（log, sqrt, square等）
                - columns: 要转换的列
                
        Returns:
            ExecutionResult: 执行结果，包含转换后的数据集
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
            transformation = parameters.get('transformation', 'log')
            columns = parameters.get('columns', [])
            if columns and isinstance(columns, str):
                columns = columns.split(',')
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 选择要处理的列
    columns_to_process = {repr(columns)} if {repr(columns)} else df.select_dtypes(include='number').columns.tolist()
    
    # 执行变换
    for col in columns_to_process:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            if '{transformation}' == 'log':
                # 对数变换 (加1避免对0取对数)
                df[f"{{col}}_log"] = np.log1p(df[col].abs())
            elif '{transformation}' == 'sqrt':
                # 平方根变换
                df[f"{{col}}_sqrt"] = np.sqrt(df[col].abs())
            elif '{transformation}' == 'square':
                # 平方变换
                df[f"{{col}}_squared"] = df[col] ** 2
            elif '{transformation}' == 'standardize':
                # 标准化变换 (z-score)
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    df[f"{{col}}_standardized"] = (df[col] - mean) / std
            elif '{transformation}' == 'normalize':
                # 归一化变换 (Min-Max)
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val > min_val:
                    df[f"{{col}}_normalized"] = (df[col] - min_val) / (max_val - min_val)
    
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
    raise Exception(f"特征转换失败: {{str(e)}}")
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
                    logs=[f"成功应用{transformation}转换"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '特征转换失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行特征转换器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class FeatureSelector(BaseComponentExecutor):
    """特征选择器
    
    选择数据集中重要的特征，去除不重要的特征。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        选择特征
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
            parameters: 参数，包括:
                - method: 选择方法（手动、相关性等）
                - columns: 要保留的列
                - target: 目标变量（用于相关性选择）
                
        Returns:
            ExecutionResult: 执行结果，包含选择后的数据集
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
            method = parameters.get('method', 'manual')
            columns = parameters.get('columns', [])
            if columns and isinstance(columns, str):
                columns = columns.split(',')
            target = parameters.get('target', '')
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression, f_classif, mutual_info_classif
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    if '{method}' == 'manual':
        # 手动选择列
        columns_to_keep = {repr(columns)}
        if columns_to_keep:
            # 保证所有列都在数据集中
            columns_to_keep = [col for col in columns_to_keep if col in df.columns]
            df_selected = df[columns_to_keep]
        else:
            df_selected = df.copy()
    
    elif '{method}' == 'correlation':
        # 基于相关性选择（需要目标变量）
        target_col = '{target}'
        if not target_col or target_col not in df.columns:
            raise ValueError("相关性选择需要指定有效的目标变量")
            
        # 计算与目标变量的相关性
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        if target_col in numeric_cols:
            numeric_cols.remove(target_col)
            
        # 计算相关系数
        correlations = df[numeric_cols].corrwith(df[target_col]).abs().sort_values(ascending=False)
        
        # 选择相关性最高的特征
        top_features = correlations.index.tolist()
        
        # 添加目标变量和非数值列
        selected_columns = top_features + [target_col] + [col for col in df.columns if col not in numeric_cols + [target_col]]
        df_selected = df[selected_columns]
    
    elif '{method}' == 'variance':
        # 基于方差选择（过滤低方差特征）
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        threshold = 0.01  # 方差阈值
        
        # 计算每个数值列的方差
        variances = df[numeric_cols].var()
        
        # 选择方差大于阈值的特征
        high_variance_cols = variances[variances > threshold].index.tolist()
        
        # 添加非数值列
        selected_columns = high_variance_cols + [col for col in df.columns if col not in numeric_cols]
        df_selected = df[selected_columns]
    
    else:
        df_selected = df.copy()
    
    # 获取数据信息
    info = {{
        'columns': df_selected.columns.tolist(),
        'shape': df_selected.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df_selected.columns, df_selected.dtypes)}},
        'head': df_selected.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df_selected.to_json(orient='split'),
        'info': info
    }}
except Exception as e:
    raise Exception(f"特征选择失败: {{str(e)}}")
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
                    logs=[f"特征选择完成，使用{method}方法"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '特征选择失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行特征选择器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class DataSplitter(BaseComponentExecutor):
    """数据集拆分器
    
    将数据集拆分为训练集和测试集。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        拆分数据集
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
                - input: 输入数据集（兼容旧端口名）
            parameters: 参数，包括:
                - test_size: 测试集比例
                - random_state: 随机种子
                - stratify: 是否使用分层抽样
                - stratify_column: 用于分层抽样的列名
                
        Returns:
            ExecutionResult: 执行结果，包含拆分后的训练集和测试集
        """
        try:
            # 导入必要库
            import pandas as pd
            import numpy as np
            import io
            from sklearn.model_selection import train_test_split
            
            # 获取输入数据 - 支持新旧端口名称
            dataset = None
            if 'dataset' in inputs:
                dataset = inputs['dataset']
            elif 'input' in inputs:
                dataset = inputs['input']
            else:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集，请检查端口连接"
                )
            
            # 获取参数
            test_size = float(parameters.get('test_size', 0.2))
            random_state = int(parameters.get('random_state', 42))
            stratify_param = parameters.get('stratify', False)
            stratify = stratify_param if isinstance(stratify_param, bool) else stratify_param in ['true', 'True', True]
            stratify_column = parameters.get('stratify_column', '')
            
            # 首先尝试提取完整数据（full_data），如果不存在，再使用预览数据（data）
            data_to_process = dataset.get('full_data', dataset.get('data', None))
            if not data_to_process:
                return ExecutionResult(
                    success=False,
                    error_message="输入数据集不包含有效数据"
                )
            
            # 解析输入数据集
            try:
                df = pd.read_json(io.StringIO(data_to_process), orient='split')
            except Exception as e:
                logger.error(f"解析输入数据失败: {str(e)}")
                return ExecutionResult(
                    success=False,
                    error_message=f"解析输入JSON数据失败: {str(e)}"
                )
            
            # 设置分层抽样
            stratify_col = None
            if stratify and stratify_column and stratify_column in df.columns:
                stratify_col = df[stratify_column]
                logger.info(f"使用分层抽样，基于列: {stratify_column}")
            
            # 拆分数据集
            train_df, test_df = train_test_split(
                df, 
                test_size=test_size, 
                random_state=random_state,
                stratify=stratify_col
            )
            
            # 获取训练集信息
            train_info = {
                'columns': train_df.columns.tolist(),
                'shape': train_df.shape,
                'dtypes': {str(col): str(dtype) for col, dtype in train_df.dtypes.items()},
                'head_dict': train_df.head(5).to_dict(orient='records')
            }
            
            # 获取测试集信息
            test_info = {
                'columns': test_df.columns.tolist(),
                'shape': test_df.shape,
                'dtypes': {str(col): str(dtype) for col, dtype in test_df.dtypes.items()},
                'head_dict': test_df.head(5).to_dict(orient='records')
            }
            
            # 创建预览数据（仅取部分行）
            preview_rows = min(50, train_df.shape[0])
            train_preview_df = train_df.head(preview_rows)
            test_preview_df = test_df.head(preview_rows)
            
            # 准备输出
            train_output = {
                'data': train_preview_df.to_json(orient='split'),  # 预览数据
                'info': train_info,
                'full_data': train_df.to_json(orient='split')  # 完整数据
            }
            
            test_output = {
                'data': test_preview_df.to_json(orient='split'),  # 预览数据
                'info': test_info,
                'full_data': test_df.to_json(orient='split')  # 完整数据
            }
            return ExecutionResult(
                success=True,
                outputs={
                    'train_dataset': train_output,
                    'test_dataset': test_output
                },
                logs=[f"成功拆分数据集: 训练集{1-test_size:.0%} ({train_df.shape[0]}行), 测试集{test_size:.0%} ({test_df.shape[0]}行)"]
            )
                
        except Exception as e:
            logger.error(f"执行数据集拆分器时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return ExecutionResult(
                success=False,
                error_message=str(e),
                logs=[traceback.format_exc()]
            )


class StandardScaler(BaseComponentExecutor):
    """标准化缩放器
    
    对数据进行标准化处理（均值为0，标准差为1）。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        标准化数据
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
            parameters: 参数，包括:
                - columns: 要标准化的列（为空则处理所有数值列）
                
        Returns:
            ExecutionResult: 执行结果，包含标准化后的数据集
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
            columns = parameters.get('columns', [])
            if columns and isinstance(columns, str):
                columns = columns.split(',')
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import StandardScaler as SklearnStandardScaler
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 选择要处理的列
    columns_to_process = {repr(columns)} if {repr(columns)} else df.select_dtypes(include='number').columns.tolist()
    columns_to_process = [col for col in columns_to_process if col in df.columns]
    
    if columns_to_process:
        # 创建StandardScaler
        scaler = SklearnStandardScaler()
        
        # 对数据进行标准化
        df_scaled = df.copy()
        df_scaled[columns_to_process] = scaler.fit_transform(df[columns_to_process])
        
        # 保存缩放器参数
        scaler_params = {{
            'mean': scaler.mean_.tolist(),
            'scale': scaler.scale_.tolist(),
            'columns': columns_to_process
        }}
    else:
        df_scaled = df.copy()
        scaler_params = None
    
    # 获取数据信息
    info = {{
        'columns': df_scaled.columns.tolist(),
        'shape': df_scaled.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df_scaled.columns, df_scaled.dtypes)}},
        'head': df_scaled.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df_scaled.to_json(orient='split'),
        'info': info,
        'scaler_params': scaler_params
    }}
except Exception as e:
    raise Exception(f"标准化缩放失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': {
                            'data': data_result.get('data'),
                            'info': data_result.get('info')
                        },
                        'scaler_params': data_result.get('scaler_params')
                    },
                    logs=["标准化缩放完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '标准化缩放失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行标准化缩放器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class MinMaxScaler(BaseComponentExecutor):
    """最小最大缩放器
    
    对数据进行归一化处理（缩放到[0,1]区间）。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        归一化数据
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
            parameters: 参数，包括:
                - columns: 要归一化的列（为空则处理所有数值列）
                - feature_range: 缩放范围，格式为"最小值,最大值"
                
        Returns:
            ExecutionResult: 执行结果，包含归一化后的数据集
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
            columns = parameters.get('columns', [])
            if columns and isinstance(columns, str):
                columns = columns.split(',')
            
            feature_range = parameters.get('feature_range', '0,1')
            try:
                min_val, max_val = map(float, feature_range.split(','))
                feature_range = (min_val, max_val)
            except:
                feature_range = (0, 1)
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import MinMaxScaler as SklearnMinMaxScaler
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 选择要处理的列
    columns_to_process = {repr(columns)} if {repr(columns)} else df.select_dtypes(include='number').columns.tolist()
    columns_to_process = [col for col in columns_to_process if col in df.columns]
    
    if columns_to_process:
        # 创建MinMaxScaler
        scaler = SklearnMinMaxScaler(feature_range={feature_range})
        
        # 对数据进行归一化
        df_scaled = df.copy()
        df_scaled[columns_to_process] = scaler.fit_transform(df[columns_to_process])
        
        # 保存缩放器参数
        scaler_params = {{
            'min': scaler.min_.tolist(),
            'scale': scaler.scale_.tolist(),
            'data_min': scaler.data_min_.tolist(),
            'data_max': scaler.data_max_.tolist(),
            'feature_range': {repr(feature_range)},
            'columns': columns_to_process
        }}
    else:
        df_scaled = df.copy()
        scaler_params = None
    
    # 获取数据信息
    info = {{
        'columns': df_scaled.columns.tolist(),
        'shape': df_scaled.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df_scaled.columns, df_scaled.dtypes)}},
        'head': df_scaled.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df_scaled.to_json(orient='split'),
        'info': info,
        'scaler_params': scaler_params
    }}
except Exception as e:
    raise Exception(f"归一化缩放失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': {
                            'data': data_result.get('data'),
                            'info': data_result.get('info')
                        },
                        'scaler_params': data_result.get('scaler_params')
                    },
                    logs=["归一化缩放完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '归一化缩放失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行归一化缩放器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class LabelEncoder(BaseComponentExecutor):
    """标签编码器
    
    将分类特征转换为整数标签。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        对分类特征进行标签编码
        
        Args:
            inputs: 输入数据，包括:
                - input: 输入数据集（旧端口名称）
                - dataset: 输入数据集（新端口名称）
            parameters: 参数，包括:
                - column: 要编码的列
                - output_column: 输出列名（可选）
                - store_mapping: 是否保存映射关系
                
        Returns:
            ExecutionResult: 执行结果，包含编码后的数据集和映射关系
        """
        try:
            # 获取输入数据 - 支持新旧端口名称
            dataset = None
            if 'dataset' in inputs:
                dataset = inputs['dataset']
            elif 'input' in inputs:
                dataset = inputs['input']
            else:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集，请检查端口连接"
                )
            
            # 1. 从输入解析DataFrame
            try:
                import pandas as pd
                from sklearn.preprocessing import LabelEncoder as SKLabelEncoder
                import numpy as np
                import io
                
                if isinstance(dataset, dict) and ('full_data' in dataset or 'data' in dataset):
                    # 优先使用full_data，如果不存在则回退到data
                    data_to_process = dataset.get('full_data', dataset.get('data', None))
                    if data_to_process:
                        if isinstance(data_to_process, str):
                            # 使用StringIO处理JSON字符串，解决FutureWarning
                            df = pd.read_json(io.StringIO(data_to_process), orient='split')
                        else:
                            df = pd.DataFrame(data_to_process)
                    else:
                        return ExecutionResult(
                            success=False,
                            error_message="输入数据集不包含有效数据"
                        )
                elif isinstance(dataset, list):
                    # 如果输入是列表，直接转换为DataFrame
                    df = pd.DataFrame(dataset)
                else:
                    return ExecutionResult(
                        success=False,
                        error_message=f"无法解析的输入数据格式: {type(dataset)}"
                    )
                
                # 2. 获取参数
                column = parameters.get('column', '')
                output_column = parameters.get('output_column', '')
                store_mapping = parameters.get('store_mapping', True)
                
                if not column or column not in df.columns:
                    return ExecutionResult(
                        success=False,
                        error_message=f"无效的列名: {column}"
                    )
                
                # 如果未提供输出列名，则使用原列名
                if not output_column:
                    output_column = f"{column}"
                
                # 3. 执行标签编码
                encoder = SKLabelEncoder()
                
                # 处理可能的缺失值
                # 首先获取非空值的索引
                non_null_mask = df[column].notna()
                # 仅对非空值进行编码
                if non_null_mask.any():
                    df.loc[non_null_mask, output_column] = encoder.fit_transform(df.loc[non_null_mask, column].astype(str))
                    # 缺失值将保持为NaN
                
                # 4. 创建映射关系
                label_mapping = {}
                if store_mapping:
                    label_mapping = {str(cls): int(idx) for idx, cls in enumerate(encoder.classes_)}
                
                # 5. 准备输出信息
                # 生成数据预览
                preview_rows = min(50, len(df))
                preview_df = df.head(preview_rows)
                
                # 提取元数据
                info = {
                    'columns': df.columns.tolist(),
                    'shape': df.shape,
                    'dtypes': {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)},
                    'head': df.head(5).to_dict(orient='records'),
                    'mapping': label_mapping
                }
                
                # 6. 输出结果 - 使用与其他组件一致的输出结构
                output_data = {
                    'data': preview_df.to_json(orient='split'),  # 预览数据
                    'info': info,
                    'full_data': df.to_json(orient='split')  # 完整数据
                }
                
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': output_data,  # 保留原有的dataset输出端口
                        'output': output_data,   # 添加新的output输出端口
                        'mapping': label_mapping
                    },
                    logs=[
                        f"成功对列 '{column}' 进行标签编码",
                        f"生成编码列 '{output_column}'"
                    ]
                )
                
            except Exception as e:
                error_msg = f"处理数据过程中出错: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                return ExecutionResult(
                    success=False,
                    error_message=error_msg,
                    logs=[traceback.format_exc()]
                )
            
        except Exception as e:
            error_message = f"标签编码执行出错: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            return ExecutionResult(
                success=False,
                error_message=error_message,
                logs=[traceback.format_exc()]
            )


class OneHotEncoder(BaseComponentExecutor):
    """独热编码器
    
    将分类特征转换为独热编码向量。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        对分类特征进行独热编码
        
        Args:
            inputs: 输入数据，包括:
                - input: 输入数据集
            parameters: 参数，包括:
                - columns: 要编码的列（为空则自动检测类别特征）
                - drop: 是否删除第一个类别
                - handle_unknown: 如何处理未知类别
                
        Returns:
            ExecutionResult: 执行结果，包含编码后的数据集
        """
        try:
            # 获取输入数据
            if 'input' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['input']
            
            # 获取参数
            columns = parameters.get('columns', '')
            if columns and isinstance(columns, str):
                columns = [col.strip() for col in columns.split(',')]
            
            drop = parameters.get('drop', 'first')
            handle_unknown = parameters.get('handle_unknown', 'error')
            
            # 转换为Python代码
            code = """
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder

# 加载数据
data = pd.read_json(r'''{}''')

# 确定要编码的列
columns = {}
if not columns:
    # 自动检测类别特征
    columns = data.select_dtypes(include=['object', 'category']).columns.tolist()

# 创建编码后的数据集副本
original_cols = [col for col in data.columns if col not in columns]
encoded_data = data[original_cols].copy()

# 保存编码器配置
encoder_config = {{
    'type': 'one_hot_encoder',
    'columns': columns,
    'drop': '{}',
    'handle_unknown': '{}'
}}

# 特征名映射
feature_names = {{}}

# 对每个指定列进行独热编码
for col in columns:
    if col in data.columns:
        encoder = OneHotEncoder(sparse=False, drop='{}', handle_unknown='{}')
        encoded = encoder.fit_transform(data[[col]])
        
        # 获取特征名
        categories = encoder.categories_[0]
        if '{}' == 'first':
            categories = categories[1:]
        
        # 创建特征名
        col_names = [f"{{col}}_{cat}" for cat in categories]
        feature_names[col] = col_names
        
        # 将编码结果添加到数据框
        encoded_df = pd.DataFrame(encoded, columns=col_names, index=data.index)
        encoded_data = pd.concat([encoded_data, encoded_df], axis=1)

# 添加到编码器配置
encoder_config['feature_names'] = feature_names

# 将结果转换为JSON
result = {{
    'data': encoded_data.to_json(orient='records'),
    'encoder_config': encoder_config
}}

print(json.dumps(result))
""".format(json.dumps(dataset), columns, drop, handle_unknown, drop, handle_unknown, drop)
            
            # 执行代码并获取结果
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"独热编码执行失败: {output}"
                )
                
            # 解析输出
            result = json.loads(output)
            encoded_dataset = json.loads(result['data'])
            encoder_config = result['encoder_config']
            
            return ExecutionResult(
                success=True,
                output={
                    'output': encoded_dataset,
                    'encoder_config': encoder_config
                }
            )
            
        except Exception as e:
            error_message = f"独热编码执行出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )


class CategoricalEncoder(BaseComponentExecutor):
    """类别特征编码器
    
    统一处理多种类别特征编码方法，包括独热编码、标签编码、序数编码、频率编码等。
    对应前端组件ID: encoding-categorical
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        对分类特征进行编码
        
        Args:
            inputs: 输入数据，包括:
                - input: 输入数据集
            parameters: 参数，包括:
                - encoding_method: 编码方法（one_hot, label, ordinal, frequency, binary）
                - columns: 要编码的列（为空则自动检测类别特征）
                - handle_unknown: 如何处理未知类别（error, ignore, use_na）
                
        Returns:
            ExecutionResult: 执行结果，包含编码后的数据集
        """
        try:
            # 获取输入数据
            if 'input' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['input']
            
            # 获取参数
            encoding_method = parameters.get('encoding_method', 'one_hot')
            columns = parameters.get('columns', '')
            handle_unknown = parameters.get('handle_unknown', 'error')
            
            if columns and isinstance(columns, str):
                columns = [col.strip() for col in columns.split(',') if col.strip()]
            
            # 根据编码方法转换为Python代码
            code = """
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, LabelEncoder, OrdinalEncoder
from category_encoders import BinaryEncoder
import json

# 加载数据
data = pd.read_json(r'''{}''')

# 编码方法
encoding_method = '{}'

# 确定要编码的列
columns = {}
if not columns:
    # 自动检测类别特征
    columns = data.select_dtypes(include=['object', 'category']).columns.tolist()

# 创建编码后的数据集副本
encoded_data = data.copy()
encoder_config = {{
    'type': encoding_method,
    'columns': columns,
    'handle_unknown': '{}'
}}

# 根据编码方法进行处理
if encoding_method == 'one_hot':
    # 独热编码
    original_cols = [col for col in data.columns if col not in columns]
    encoded_data = data[original_cols].copy()
    
    # 特征名映射
    feature_names = {{}}
    
    # 对每个指定列进行独热编码
    for col in columns:
        if col in data.columns:
            encoder = OneHotEncoder(sparse=False, handle_unknown='{}')
            encoded = encoder.fit_transform(data[[col]])
            
            # 获取特征名
            categories = encoder.categories_[0]
            
            # 创建特征名
            col_names = [f"{{col}}_{cat}" for cat in categories]
            feature_names[col] = col_names
            
            # 将编码结果添加到数据框
            encoded_df = pd.DataFrame(encoded, columns=col_names, index=data.index)
            encoded_data = pd.concat([encoded_data, encoded_df], axis=1)
    
    # 添加到编码器配置
    encoder_config['feature_names'] = feature_names

elif encoding_method == 'label':
    # 标签编码
    label_mappings = {{}}
    
    # 对每个指定列进行标签编码
    for col in columns:
        if col in data.columns:
            le = LabelEncoder()
            encoded_data[col] = le.fit_transform(data[col].astype(str))
            
            # 保存类别映射
            label_mappings[col] = {{str(v): int(i) for i, v in enumerate(le.classes_)}}
    
    # 添加到编码器配置
    encoder_config['label_mappings'] = label_mappings

elif encoding_method == 'ordinal':
    # 序数编码 - 可以指定顺序，但这里使用默认顺序
    ordinal_mappings = {{}}
    
    # 对每个指定列进行序数编码
    for col in columns:
        if col in data.columns:
            # 获取唯一值并排序
            categories = sorted(data[col].unique())
            mapping = {{cat: i for i, cat in enumerate(categories)}}
            
            # 应用映射
            encoded_data[col] = data[col].map(mapping)
            
            # 保存映射
            ordinal_mappings[col] = mapping
    
    # 添加到编码器配置
    encoder_config['ordinal_mappings'] = ordinal_mappings

elif encoding_method == 'frequency':
    # 频率编码 - 用类别出现的频率替换类别
    frequency_mappings = {{}}
    
    # 对每个指定列进行频率编码
    for col in columns:
        if col in data.columns:
            # 计算每个类别的频率
            freq = data[col].value_counts(normalize=True).to_dict()
            
            # 应用频率映射
            encoded_data[col] = data[col].map(freq)
            
            # 保存映射
            frequency_mappings[col] = freq
    
    # 添加到编码器配置
    encoder_config['frequency_mappings'] = frequency_mappings

elif encoding_method == 'binary':
    try:
        # 二进制编码 - 需要安装 category_encoders 包
        # 在容器中预先安装：pip install category-encoders
        
        # 选择要编码的列
        cols_to_encode = [col for col in columns if col in data.columns]
        
        if cols_to_encode:
            # 创建编码器
            encoder = BinaryEncoder(cols=cols_to_encode)
            
            # 应用编码
            binary_encoded = encoder.fit_transform(data)
            
            # 合并数据
            non_encoded_cols = [col for col in data.columns if col not in cols_to_encode]
            encoded_data = pd.concat([data[non_encoded_cols], binary_encoded], axis=1)
            
            # 保存编码器配置
            encoder_config['binary_columns'] = cols_to_encode
    except ImportError:
        raise Exception("二进制编码需要安装 category_encoders 包。请在容器中运行: pip install category-encoders")

else:
    raise ValueError(f"不支持的编码方法: {{encoding_method}}")

# 将结果转换为JSON
result = {{
    'data': encoded_data.to_json(orient='records'),
    'encoder_config': encoder_config
}}

print(json.dumps(result))
""".format(json.dumps(dataset), encoding_method, columns, handle_unknown, handle_unknown)
            
            # 执行代码并获取结果
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"类别特征编码执行失败: {output}"
                )
                
            # 解析输出
            result = json.loads(output)
            encoded_dataset = json.loads(result['data'])
            encoder_config = result['encoder_config']
            
            return ExecutionResult(
                success=True,
                output={
                    'output': encoded_dataset,
                    'encoder_config': encoder_config
                }
            )
            
        except Exception as e:
            error_message = f"类别特征编码执行出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )


class FeatureEngineer(BaseComponentExecutor):
    """特征工程组件
    
    创建新特征或转换现有特征，支持多项式特征、交互特征、特征分箱和自定义公式。
    对应前端组件ID: feature-engineering
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        执行特征工程
        
        Args:
            inputs: 输入数据，包括:
                - input: 输入数据集
            parameters: 参数，包括:
                - operations: 特征操作（polynomial, interaction, binning, custom）
                - columns: 要处理的列
                - degree: 多项式次数
                - n_bins: 分箱数量
                - formula: 自定义公式
                
        Returns:
            ExecutionResult: 执行结果，包含特征工程后的数据集
        """
        try:
            # 获取输入数据
            if 'input' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['input']
            
            # 获取参数
            operation = parameters.get('operations', 'polynomial')
            columns_str = parameters.get('columns', '')
            columns = [col.strip() for col in columns_str.split(',') if col.strip()] if columns_str else []
            degree = parameters.get('degree', 2)
            n_bins = parameters.get('n_bins', 5)
            formula = parameters.get('formula', '')
            
            # 根据不同操作转换为Python代码
            code = """
import pandas as pd
import numpy as np
from sklearn.preprocessing import PolynomialFeatures, KBinsDiscretizer
import re
import json

# 加载数据
data = pd.read_json(r'''{}''')

# 特征工程操作类型
operation = '{}'
columns = {}
degree = {}
n_bins = {}
formula = '{}'

# 创建结果数据集
result_data = data.copy()
feature_info = {{
    'operation': operation,
    'source_columns': columns,
    'new_columns': []
}}

try:
    # 检查列是否存在
    if columns:
        missing_cols = [col for col in columns if col not in data.columns]
        if missing_cols:
            raise ValueError(f"以下列不存在于数据集中: {{missing_cols}}")
    
    # 执行特定的特征工程操作
    if operation == 'polynomial':
        # 多项式特征
        if not columns:
            # 如果没有指定列，使用所有数值列
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            columns = numeric_cols
        
        # 选择要处理的列
        X = data[columns]
        
        # 创建多项式特征
        poly = PolynomialFeatures(degree=degree, include_bias=False)
        poly_features = poly.fit_transform(X)
        
        # 生成特征名
        if degree == 2:
            # 对于2次多项式，手动生成更可读的名称
            feature_names = []
            for i, col1 in enumerate(columns):
                feature_names.append(col1)  # 原始特征
                for j, col2 in enumerate(columns[i:], i):
                    if i == j:
                        feature_names.append(f"{col1}^2")  # 平方项
                    else:
                        feature_names.append(f"{col1}*{col2}")  # 交互项
        else:
            # 对于更高次多项式，使用sklearn生成的名称
            feature_names = poly.get_feature_names_out(columns)
        
        # 创建多项式特征数据框
        poly_df = pd.DataFrame(poly_features, columns=feature_names, index=data.index)
        
        # 移除原始列（因为它们包含在多项式特征中）
        non_poly_cols = [col for col in data.columns if col not in columns]
        result_data = pd.concat([data[non_poly_cols], poly_df], axis=1)
        
        # 记录新增的列
        feature_info['new_columns'] = feature_names.tolist()
        feature_info['degree'] = degree
        
    elif operation == 'interaction':
        # 交互特征（仅考虑两两交互）
        if not columns or len(columns) < 2:
            # 至少需要两列才能创建交互项
            raise ValueError("交互项特征至少需要指定两列")
        
        # 选择要处理的列
        X = data[columns]
        
        # 创建所有可能的列对组合
        interaction_features = []
        interaction_names = []
        
        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns[i+1:], i+1):
                # 创建交互特征
                interaction = data[col1] * data[col2]
                interaction_name = f"{col1}*{col2}"
                
                # 添加到结果中
                result_data[interaction_name] = interaction
                interaction_names.append(interaction_name)
        
        # 记录新增的列
        feature_info['new_columns'] = interaction_names
        
    elif operation == 'binning':
        # 特征分箱
        if not columns:
            # 如果没有指定列，使用所有数值列
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            columns = numeric_cols
        
        # 选择要处理的列
        X = data[columns]
        
        # 为每列创建分箱
        binned_columns = []
        for col in columns:
            # 创建分箱器
            binner = KBinsDiscretizer(n_bins=n_bins, encode='ordinal', strategy='quantile')
            binned_values = binner.fit_transform(data[[col]])
            
            # 添加到结果中
            bin_col_name = f"{col}_bin"
            result_data[bin_col_name] = binned_values
            binned_columns.append(bin_col_name)
            
            # 创建分桶边界信息
            bin_edges = binner.bin_edges_[0]
            feature_info[f"{col}_bin_edges"] = bin_edges.tolist()
        
        # 记录新增的列
        feature_info['new_columns'] = binned_columns
        feature_info['n_bins'] = n_bins
        
    elif operation == 'custom':
        # 自定义公式特征
        if not formula:
            raise ValueError("自定义特征需要提供公式")
        
        # 解析公式，支持基本操作: 列名、四则运算、log、exp、sqrt等
        # 分割公式为多个表达式（如果有多个公式用逗号分隔）
        expressions = [expr.strip() for expr in formula.split(',')]
        
        # 为每个表达式创建新特征
        custom_columns = []
        for idx, expr in enumerate(expressions):
            try:
                # 生成特征名 - 使用表达式作为名称
                feature_name = f"custom_{idx+1}"
                
                # 将表达式中的列名替换为data[列名]
                pattern = r'\\b([a-zA-Z_][a-zA-Z0-9_]*)\\b'
                columns_in_expr = re.findall(pattern, expr)
                
                # 检查所有列是否存在
                for col in columns_in_expr:
                    if col not in data.columns and col not in ['log', 'exp', 'sqrt', 'sin', 'cos', 'tan']:
                        raise ValueError(f"列 '{col}' 不存在于数据集中")
                
                # 构建Python代码
                py_expr = expr
                for col in columns_in_expr:
                    if col not in ['log', 'exp', 'sqrt', 'sin', 'cos', 'tan']:
                        py_expr = re.sub(r'\\b' + col + r'\\b', f"data['{col}']", py_expr)
                
                # 计算结果
                result = eval(py_expr)
                result_data[feature_name] = result
                custom_columns.append(feature_name)
                
                # 记录原始表达式
                feature_info[f"expr_{idx+1}"] = expr
                
            except Exception as e:
                raise ValueError(f"表达式 '{expr}' 计算错误: {str(e)}")
        
        # 记录新增的列
        feature_info['new_columns'] = custom_columns
        feature_info['expressions'] = expressions
        
    else:
        raise ValueError(f"不支持的特征工程操作: {operation}")
    
except Exception as e:
    # 捕获并重新抛出错误，以便在外部处理
    raise Exception(f"特征工程失败: {str(e)}")

# 将结果转换为JSON
output = {{
    'data': result_data.to_json(orient='records'),
    'feature_info': feature_info
}}

print(json.dumps(output))
""".format(json.dumps(dataset), operation, columns, degree, n_bins, formula)
            
            # 执行代码并获取结果
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"特征工程执行失败: {output}"
                )
                
            # 解析输出
            result = json.loads(output)
            result_dataset = json.loads(result['data'])
            feature_info = result['feature_info']
            
            return ExecutionResult(
                success=True,
                output={
                    'output': result_dataset,
                    'feature_info': feature_info
                }
            )
            
        except Exception as e:
            error_message = f"特征工程执行出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )


class TextFeatureEngineering(BaseComponentExecutor):
    """文本特征工程
    
    将文本数据转换为特征向量，支持TF-IDF和Count向量化两种方法。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        对文本数据进行特征工程
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集，包含要处理的文本列
            parameters: 参数，包括:
                - method: 向量化方法 ('tfidf' 或 'count')
                - text_column: 要处理的文本列
                - max_features: 最大特征数量
                - min_df: 最小文档频率
                - max_df: 最大文档频率
                - ngram_range: n-gram范围
                - stop_words: 是否使用停用词
                - output_format: 输出格式 ('dense' 或 'sparse')
                
        Returns:
            ExecutionResult: 执行结果，包含特征工程后的数据集
        """
        try:
            # 导入必要库
            import pandas as pd
            import numpy as np
            import io
            import json
            from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
            import scipy.sparse as sp
            
            # 获取输入数据
            if 'dataset' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['dataset']
            
            # 首先尝试提取完整数据（full_data），如果不存在，再使用预览数据（data）
            data_to_process = dataset.get('full_data', dataset.get('data', None))
            if not data_to_process:
                return ExecutionResult(
                    success=False,
                    error_message="输入数据集不包含有效数据"
                )

            # 获取参数
            method = parameters.get('method', 'tfidf')
            text_column = parameters.get('text_column', '')
            max_features = parameters.get('max_features', 100)
            min_df = parameters.get('min_df', 2)
            max_df = parameters.get('max_df', 0.8)
            ngram_range_str = parameters.get('ngram_range', '1,1')
            stop_words = parameters.get('stop_words', 'english')
            output_format = parameters.get('output_format', 'dense')
            
            # 参数处理和验证
            if not text_column:
                return ExecutionResult(
                    success=False,
                    error_message="请指定要处理的文本列"
                )
                
            try:
                max_features = int(max_features)
            except (ValueError, TypeError):
                max_features = 100
                
            try:
                if isinstance(min_df, str) and '.' in min_df:
                    min_df = float(min_df)
                else:
                    min_df = int(min_df)
            except (ValueError, TypeError):
                min_df = 2
                
            try:
                if isinstance(max_df, str) and '.' in max_df:
                    max_df = float(max_df)
                else:
                    max_df = int(max_df)
                # 确保max_df值在有效范围内
                if isinstance(max_df, float) and (max_df <= 0.0 or max_df > 1.0):
                    logger.warning(f"max_df值{max_df}超出有效浮点数范围[0.0, 1.0]，将使用默认值0.8")
                    max_df = 0.8
                elif isinstance(max_df, int) and max_df < 1:
                    logger.warning(f"max_df值{max_df}超出有效整数范围[1, inf)，将使用默认值0.8")
                    max_df = 0.8
            except (ValueError, TypeError):
                max_df = 0.8
                
            # 解析n-gram范围
            try:
                if isinstance(ngram_range_str, str):
                    parts = ngram_range_str.split(',')
                    if len(parts) == 2:
                        ngram_min = int(parts[0].strip())
                        ngram_max = int(parts[1].strip())
                        ngram_range = (ngram_min, ngram_max)
                    else:
                        ngram_range = (1, 1)
                else:
                    ngram_range = (1, 1)
            except (ValueError, TypeError):
                ngram_range = (1, 1)
                
            # 验证stop_words
            if stop_words not in ['english', 'none']:
                stop_words = 'english' if stop_words else None
            elif stop_words == 'none':
                stop_words = None
            
            # 解析输入数据集
            try:
                df = pd.read_json(io.StringIO(data_to_process), orient='split')
            except Exception as e:
                logger.error(f"解析输入数据失败: {str(e)}")
                return ExecutionResult(
                    success=False,
                    error_message=f"解析输入JSON数据失败: {str(e)}"
                )
            
            # 验证文本列是否存在
            if text_column not in df.columns:
                return ExecutionResult(
                    success=False,
                    error_message=f"文本列 '{text_column}' 不存在于数据集中"
                )
            
            # 检查文本列是否包含缺失值，并处理
            if df[text_column].isna().any():
                df[text_column] = df[text_column].fillna('')
            
            # 设置向量化器参数
            vectorizer_params = {
                'max_features': max_features,
                'min_df': min_df,
                'max_df': max_df,
                'ngram_range': ngram_range,
                'stop_words': stop_words
            }
            
            # 初始化向量化器
            if method == 'tfidf':
                vectorizer = TfidfVectorizer(**vectorizer_params)
            else:  # 'count'
                vectorizer = CountVectorizer(**vectorizer_params)
            
            # 对文本列进行向量化
            X = vectorizer.fit_transform(df[text_column])
            
            # 获取特征名称
            feature_names = vectorizer.get_feature_names_out()
            
            # 创建特征矩阵的DataFrame
            if output_format == 'dense':
                # 转换为密集矩阵
                X_dense = X.toarray()
                # 创建特征列名
                feature_columns = [f'{text_column}_{feat}' for feat in feature_names]
                # 创建特征DataFrame
                feature_df = pd.DataFrame(X_dense, columns=feature_columns)
            else:  # 'sparse'
                # 保持为稀疏矩阵，只创建最重要的几个特征列
                X_dense = X.toarray()
                # 为每一行找出最重要的N个特征索引
                top_n = min(10, X.shape[1])  # 最多取10个特征
                feature_columns = []
                feature_data = []
                
                for i in range(X.shape[0]):
                    row_data = {}
                    # 获取这一行中值最大的top_n个特征索引
                    row = X[i].toarray().flatten() if sp.issparse(X[i]) else X[i]
                    top_indices = row.argsort()[-top_n:][::-1]
                    
                    for idx in top_indices:
                        if row[idx] > 0:  # 只记录非零特征
                            feat_name = f'{text_column}_{feature_names[idx]}'
                            if feat_name not in feature_columns:
                                feature_columns.append(feat_name)
                            row_data[feat_name] = row[idx]
                    
                    feature_data.append(row_data)
                
                # 创建特征DataFrame
                feature_df = pd.DataFrame(feature_data)
            
            # 获取向量化器的词汇表大小
            vocab_size = len(vectorizer.vocabulary_)
            
            # 合并原始DataFrame和特征DataFrame
            result_df = pd.concat([df.reset_index(drop=True), feature_df.reset_index(drop=True)], axis=1)
            
            # 获取数据信息
            info = {
                'columns': result_df.columns.tolist(),
                'shape': result_df.shape,
                'dtypes': {col: str(dtype) for col, dtype in zip(result_df.columns, result_df.dtypes)},
                'vectorizer_info': {
                    'method': method,
                    'vocab_size': vocab_size,
                    'n_features': X.shape[1],
                    'feature_names': feature_names[:20].tolist() + (['...'] if len(feature_names) > 20 else [])
                }
            }
            
            # 创建预览数据（仅取部分列和行）
            preview_cols = df.columns.tolist() + feature_columns[:10]
            preview_rows = min(50, result_df.shape[0])
            preview_df = result_df[preview_cols].head(preview_rows)
            
            # 准备输出
            output_data = {
                'data': preview_df.to_json(orient='split'),  # 预览数据
                'info': info,
                'full_data': result_df.to_json(orient='split')  # 完整数据
            }
            
            return ExecutionResult(
                success=True,
                outputs={'output': output_data},
                logs=[f"成功应用{method}向量化方法处理文本特征"]
            )
                
        except Exception as e:
            logger.error(f"执行文本特征工程时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e),
                logs=[traceback.format_exc()]
            )


class NumericFeatureEngineering(BaseComponentExecutor):
    """数值特征工程
    
    对数值数据进行特征工程，包括多项式特征、交互特征等。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        对数值数据进行特征工程
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集，包含要处理的数值列
            parameters: 参数，包括:
                - method: 特征工程方法 ('polynomial', 'interaction', 'binning')
                - columns: 要处理的数值列
                - degree: 多项式阶数（用于polynomial方法）
                - bins: 分箱数量（用于binning方法）
                
        Returns:
            ExecutionResult: 执行结果，包含特征工程后的数据集
        """
        try:
            # 导入必要库
            import pandas as pd
            import numpy as np
            import io
            from sklearn.preprocessing import PolynomialFeatures
            
            # 获取输入数据
            if 'dataset' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['dataset']
            
            # 首先尝试提取完整数据（full_data），如果不存在，再使用预览数据（data）
            data_to_process = dataset.get('full_data', dataset.get('data', None))
            if not data_to_process:
                return ExecutionResult(
                    success=False,
                    error_message="输入数据集不包含有效数据"
                )

            # 获取参数
            method = parameters.get('method', 'polynomial')
            columns = parameters.get('columns', [])
            degree = parameters.get('degree', 2)
            bins = parameters.get('bins', 5)
            
            # 处理列参数
            if isinstance(columns, str):
                columns = [col.strip() for col in columns.split(',') if col.strip()]
            
            # 参数处理和验证
            try:
                degree = int(degree)
                if degree < 1:
                    degree = 2
            except (ValueError, TypeError):
                degree = 2
                
            try:
                bins = int(bins)
                if bins < 2:
                    bins = 5
            except (ValueError, TypeError):
                bins = 5
            
            # 解析输入数据集
            try:
                df = pd.read_json(io.StringIO(data_to_process), orient='split')
            except Exception as e:
                logger.error(f"解析输入数据失败: {str(e)}")
                return ExecutionResult(
                    success=False,
                    error_message=f"解析输入JSON数据失败: {str(e)}"
                )
            
            # 确定要处理的列
            columns_to_process = columns if columns else df.select_dtypes(include=np.number).columns.tolist()
            columns_to_process = [col for col in columns_to_process if col in df.columns]
            
            if not columns_to_process:
                return ExecutionResult(
                    success=False,
                    error_message="数据集中没有可处理的数值列"
                )
            
            # 提取要处理的特征
            X = df[columns_to_process]
            
            # 应用特征工程方法
            if method == 'polynomial':
                # 多项式特征
                poly = PolynomialFeatures(degree=degree, include_bias=False)
                X_poly = poly.fit_transform(X)
                
                # 创建特征名称
                feature_names = poly.get_feature_names_out(columns_to_process)
                
                # 创建特征DataFrame
                poly_df = pd.DataFrame(X_poly, columns=feature_names)
                
                # 从poly_df中排除已经在原始数据中存在的列
                new_features_df = poly_df.loc[:, ~poly_df.columns.isin(columns_to_process)]
                
                # 合并原始DataFrame和新特征DataFrame
                result_df = pd.concat([df.reset_index(drop=True), new_features_df.reset_index(drop=True)], axis=1)
                
                method_info = {
                    'type': 'polynomial',
                    'degree': degree,
                    'n_original_features': len(columns_to_process),
                    'n_generated_features': new_features_df.shape[1]
                }
                
            elif method == 'interaction':
                # 交互特征（只考虑二阶交互）
                n_features = len(columns_to_process)
                result_df = df.copy()
                
                # 创建所有可能的二阶交互特征
                interaction_features = []
                for i in range(n_features):
                    for j in range(i+1, n_features):
                        col1 = columns_to_process[i]
                        col2 = columns_to_process[j]
                        new_col = f"{col1}_x_{col2}"
                        result_df[new_col] = df[col1] * df[col2]
                        interaction_features.append(new_col)
                
                method_info = {
                    'type': 'interaction',
                    'n_original_features': n_features,
                    'n_generated_features': len(interaction_features),
                    'generated_features': interaction_features[:10] + (['...'] if len(interaction_features) > 10 else [])
                }
                
            elif method == 'binning':
                # 分箱特征
                result_df = df.copy()
                binned_features = []
                
                for col in columns_to_process:
                    # 创建等宽分箱
                    bins_array = np.linspace(df[col].min(), df[col].max(), bins + 1)
                    # 创建分箱特征
                    binned_col = f"{col}_binned"
                    result_df[binned_col] = pd.cut(df[col], bins=bins_array, labels=False, include_lowest=True)
                    # 将分箱结果转换为字符串类别
                    result_df[binned_col] = 'bin_' + result_df[binned_col].astype(str)
                    binned_features.append(binned_col)
                
                method_info = {
                    'type': 'binning',
                    'n_bins': bins,
                    'n_original_features': len(columns_to_process),
                    'n_generated_features': len(binned_features),
                    'generated_features': binned_features
                }
            
            else:
                return ExecutionResult(
                    success=False,
                    error_message=f"不支持的特征工程方法: {method}"
                )
            
            # 获取数据信息
            info = {
                'columns': result_df.columns.tolist(),
                'shape': result_df.shape,
                'dtypes': {col: str(dtype) for col, dtype in zip(result_df.columns, result_df.dtypes)},
                'method_info': method_info
            }
            
            # 创建预览数据
            preview_rows = min(50, result_df.shape[0])
            preview_df = result_df.head(preview_rows)
            
            # 准备输出
            output_data = {
                'data': preview_df.to_json(orient='split'),  # 预览数据
                'info': info,
                'full_data': result_df.to_json(orient='split')  # 完整数据
            }
            
            return ExecutionResult(
                success=True,
                outputs={'output': output_data},
                logs=[f"成功应用{method}方法处理数值特征"]
            )
                
        except Exception as e:
            logger.error(f"执行数值特征工程时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e),
                logs=[traceback.format_exc()]
            )
