"""
特征工程组件执行器

该模块实现了与特征工程相关的组件执行器，包括特征选择、特征转换和数据编码等。
"""

import logging
import json
import traceback
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
            parameters: 参数，包括:
                - test_size: 测试集比例
                - random_state: 随机种子
                - stratify: 是否使用分层抽样
                - target: 目标变量（用于分层抽样）
                
        Returns:
            ExecutionResult: 执行结果，包含拆分后的训练集和测试集
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
            test_size = float(parameters.get('test_size', 0.2))
            random_state = int(parameters.get('random_state', 42))
            stratify = parameters.get('stratify', 'false') == 'true'
            target = parameters.get('target', '')
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import train_test_split
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 设置分层抽样
    stratify_col = None
    if {stratify} and '{target}' and '{target}' in df.columns:
        stratify_col = df['{target}']
    
    # 拆分数据集
    train_df, test_df = train_test_split(
        df, 
        test_size={test_size}, 
        random_state={random_state},
        stratify=stratify_col
    )
    
    # 获取训练集信息
    train_info = {{
        'columns': train_df.columns.tolist(),
        'shape': train_df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(train_df.columns, train_df.dtypes)}},
        'head': train_df.head(5).to_dict(orient='records')
    }}
    
    # 获取测试集信息
    test_info = {{
        'columns': test_df.columns.tolist(),
        'shape': test_df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(test_df.columns, test_df.dtypes)}},
        'head': test_df.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'train_data': {{
            'data': train_df.to_json(orient='split'),
            'info': train_info
        }},
        'test_data': {{
            'data': test_df.to_json(orient='split'),
            'info': test_info
        }}
    }}
except Exception as e:
    raise Exception(f"数据集拆分失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'train_dataset': data_result.get('train_data', {}),
                        'test_dataset': data_result.get('test_data', {})
                    },
                    logs=[f"成功拆分数据集: 训练集{1-test_size:.0%}, 测试集{test_size:.0%}"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '数据集拆分失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行数据集拆分器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
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
                - input: 输入数据集
            parameters: 参数，包括:
                - columns: 要编码的列（为空则自动检测类别特征）
                
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
            
            # 转换为Python代码
            code = """
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

# 加载数据
data = pd.read_json(r'''{}''')

# 确定要编码的列
columns = {}
if not columns:
    # 自动检测类别特征
    columns = data.select_dtypes(include=['object', 'category']).columns.tolist()

# 创建编码后的数据集副本
encoded_data = data.copy()

# 保存编码器和类别映射
encoders = {{}}
label_mappings = {{}}

# 对每个指定列进行标签编码
for col in columns:
    if col in data.columns:
        le = LabelEncoder()
        encoded_data[col] = le.fit_transform(data[col].astype(str))
        
        # 保存类别映射
        label_mappings[col] = {{str(v): int(i) for i, v in enumerate(le.classes_)}}
        
# 保存编码器配置
encoder_config = {{
    'type': 'label_encoder',
    'columns': columns,
    'label_mappings': label_mappings
}}

# 将结果转换为JSON
result = {{
    'data': encoded_data.to_json(orient='records'),
    'encoder_config': encoder_config
}}

print(json.dumps(result))
""".format(json.dumps(dataset), columns)
            
            # 执行代码并获取结果
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"标签编码执行失败: {output}"
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
            error_message = f"标签编码执行出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
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
