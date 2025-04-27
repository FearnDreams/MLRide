"""
树模型组件执行器

该模块实现了基于树的模型组件执行器，包括决策树和随机森林等算法。
"""

import logging
import json
import traceback
from typing import Dict, Any, List
from .executors import BaseComponentExecutor, ExecutionResult
from .model_components import BaseModelTrainer

logger = logging.getLogger(__name__)

class DecisionTreeTrainer(BaseModelTrainer):
    """决策树训练器
    
    训练决策树模型，用于分类或回归任务。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        训练决策树模型
        
        Args:
            inputs: 输入数据，包括:
                - train: 训练数据集
                - test: 测试数据集（可选）
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标变量
                - max_depth: 最大深度
                - min_samples_split: 内部节点的最小样本数
                - criterion: 分裂标准（分类：gini/entropy，回归：mse/mae）
                
        Returns:
            ExecutionResult: 执行结果，包含训练好的模型和预测结果
        """
        try:
            # 获取输入数据
            if 'train' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少训练数据集"
                )
            
            train_dataset = inputs['train']
            test_dataset = inputs.get('test')
            
            # 获取参数
            features = parameters.get('features', [])
            if features and isinstance(features, str):
                features = features.split(',')
            
            target = parameters.get('target', '')
            if not target:
                return ExecutionResult(
                    success=False,
                    error_message="未指定目标变量"
                )
            
            max_depth = parameters.get('max_depth', 'None')
            if max_depth and max_depth.lower() != 'none':
                max_depth = int(max_depth)
            else:
                max_depth = None
                
            min_samples_split = int(parameters.get('min_samples_split', 2))
            criterion = parameters.get('criterion', 'auto')
            
            # 准备数据处理和模型训练代码
            data_prep_code = self._prepare_data(train_dataset, features, target)
            
            # 添加测试数据处理
            test_data_code = ""
            if test_dataset:
                test_data_code = f"""
# 解析测试数据集
test_df = pd.read_json('''{json.dumps(test_dataset.get('data', '{}'))}''', orient='split')
"""
            
            # 模型训练代码
            model_code = f"""
# 训练决策树模型
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor, export_graphviz
import io
import base64

# 根据问题类型选择合适的决策树实现
if problem_type == 'classification':
    # 分类问题
    criterion_value = '{criterion}'
    if criterion_value == 'auto':
        criterion_value = 'gini'
    
    model = DecisionTreeClassifier(
        max_depth={max_depth if max_depth else 'None'}, 
        min_samples_split={min_samples_split},
        criterion=criterion_value,
        random_state=42
    )
else:
    # 回归问题
    criterion_value = '{criterion}'
    if criterion_value == 'auto':
        criterion_value = 'squared_error'  # 等同于旧版的 'mse'
    
    model = DecisionTreeRegressor(
        max_depth={max_depth if max_depth else 'None'}, 
        min_samples_split={min_samples_split},
        criterion=criterion_value,
        random_state=42
    )

model.fit(X_train, y_train)

# 计算训练集预测值和指标
y_train_pred = model.predict(X_train)

if problem_type == 'classification':
    # 分类指标
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    
    train_metrics = {{
        'accuracy': float(accuracy_score(y_train, y_train_pred)),
        'precision': float(precision_score(y_train, y_train_pred, average='weighted', zero_division=0)),
        'recall': float(recall_score(y_train, y_train_pred, average='weighted', zero_division=0)),
        'f1': float(f1_score(y_train, y_train_pred, average='weighted', zero_division=0))
    }}
else:
    # 回归指标
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    
    train_metrics = {{
        'mse': float(mean_squared_error(y_train, y_train_pred)),
        'rmse': float(np.sqrt(mean_squared_error(y_train, y_train_pred))),
        'mae': float(mean_absolute_error(y_train, y_train_pred)),
        'r2': float(r2_score(y_train, y_train_pred))
    }}

# 获取特征重要性
feature_importance = {{feat: imp for feat, imp in zip(feature_cols, model.feature_importances_)}}

# 可视化决策树（限制为较小的树，避免过大）
tree_viz = None
if {max_depth if max_depth else 10} <= 5 or model.tree_.node_count < 50:
    try:
        dot_data = io.StringIO()
        export_graphviz(model, out_file=dot_data,
                        feature_names=feature_cols,
                        filled=True, rounded=True,
                        special_characters=True,
                        max_depth=5)  # 限制可视化深度
        tree_viz = dot_data.getvalue()
    except Exception as e:
        print(f"树可视化失败: {{str(e)}}")

# 模型对象信息
model_info = {{
    'type': 'decision_tree',
    'feature_names': feature_cols,
    'target': '{target}',
    'max_depth': model.tree_.max_depth,
    'n_nodes': model.tree_.node_count,
    'problem_type': problem_type,
    'visualization': tree_viz
}}

if problem_type == 'classification':
    model_info['classes'] = model.classes_.tolist()
"""
            
            # 添加预测代码
            prediction_code = self._generate_prediction_code('decision_tree')
            
            # 组合所有代码
            code = f"""
{data_prep_code}
{test_data_code}
{model_code}
{prediction_code}

# 返回结果
result = {{
    'model_info': model_info,
    'train_metrics': train_metrics,
    'test_results': test_results,
    'feature_importance': feature_importance
}}
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                model_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'model': model_result.get('model_info'),
                        'train_metrics': model_result.get('train_metrics'),
                        'test_results': model_result.get('test_results'),
                        'feature_importance': model_result.get('feature_importance')
                    },
                    logs=["决策树模型训练完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '决策树模型训练失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行决策树训练器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class RandomForestTrainer(BaseModelTrainer):
    """随机森林训练器
    
    训练随机森林模型，用于分类或回归任务。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        训练随机森林模型
        
        Args:
            inputs: 输入数据，包括:
                - train: 训练数据集
                - test: 测试数据集（可选）
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标变量
                - n_estimators: 树的数量
                - max_depth: 最大深度
                - max_features: 每次分裂考虑的最大特征数
                
        Returns:
            ExecutionResult: 执行结果，包含训练好的模型和预测结果
        """
        try:
            # 获取输入数据
            if 'train' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少训练数据集"
                )
            
            train_dataset = inputs['train']
            test_dataset = inputs.get('test')
            
            # 获取参数
            features = parameters.get('features', [])
            if features and isinstance(features, str):
                features = features.split(',')
            
            target = parameters.get('target', '')
            if not target:
                return ExecutionResult(
                    success=False,
                    error_message="未指定目标变量"
                )
            
            n_estimators = int(parameters.get('n_estimators', 100))
            max_depth = parameters.get('max_depth', 'None')
            if max_depth and max_depth.lower() != 'none':
                max_depth = int(max_depth)
            else:
                max_depth = None
                
            max_features = parameters.get('max_features', 'sqrt')
            
            # 准备数据处理和模型训练代码
            data_prep_code = self._prepare_data(train_dataset, features, target)
            
            # 添加测试数据处理
            test_data_code = ""
            if test_dataset:
                test_data_code = f"""
# 解析测试数据集
test_df = pd.read_json('''{json.dumps(test_dataset.get('data', '{}'))}''', orient='split')
"""
            
            # 模型训练代码
            model_code = f"""
# 训练随机森林模型
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

# 根据问题类型选择合适的随机森林实现
if problem_type == 'classification':
    # 分类问题
    model = RandomForestClassifier(
        n_estimators={n_estimators}, 
        max_depth={max_depth if max_depth else 'None'}, 
        max_features='{max_features}',
        random_state=42
    )
else:
    # 回归问题
    model = RandomForestRegressor(
        n_estimators={n_estimators}, 
        max_depth={max_depth if max_depth else 'None'}, 
        max_features='{max_features}',
        random_state=42
    )

model.fit(X_train, y_train)

# 计算训练集预测值和指标
y_train_pred = model.predict(X_train)

if problem_type == 'classification':
    # 分类指标
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    
    train_metrics = {{
        'accuracy': float(accuracy_score(y_train, y_train_pred)),
        'precision': float(precision_score(y_train, y_train_pred, average='weighted', zero_division=0)),
        'recall': float(recall_score(y_train, y_train_pred, average='weighted', zero_division=0)),
        'f1': float(f1_score(y_train, y_train_pred, average='weighted', zero_division=0))
    }}
else:
    # 回归指标
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    
    train_metrics = {{
        'mse': float(mean_squared_error(y_train, y_train_pred)),
        'rmse': float(np.sqrt(mean_squared_error(y_train, y_train_pred))),
        'mae': float(mean_absolute_error(y_train, y_train_pred)),
        'r2': float(r2_score(y_train, y_train_pred))
    }}

# 获取特征重要性
feature_importance = {{feat: imp for feat, imp in zip(feature_cols, model.feature_importances_)}}

# 模型对象信息
model_info = {{
    'type': 'random_forest',
    'feature_names': feature_cols,
    'target': '{target}',
    'n_estimators': {n_estimators},
    'max_depth': model.estimators_[0].tree_.max_depth if model.estimators_ else None,
    'problem_type': problem_type
}}

if problem_type == 'classification':
    model_info['classes'] = model.classes_.tolist()
"""
            
            # 添加预测代码
            prediction_code = self._generate_prediction_code('random_forest')
            
            # 组合所有代码
            code = f"""
{data_prep_code}
{test_data_code}
{model_code}
{prediction_code}

# 返回结果
result = {{
    'model_info': model_info,
    'train_metrics': train_metrics,
    'test_results': test_results,
    'feature_importance': feature_importance
}}
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                model_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'model': model_result.get('model_info'),
                        'train_metrics': model_result.get('train_metrics'),
                        'test_results': model_result.get('test_results'),
                        'feature_importance': model_result.get('feature_importance')
                    },
                    logs=["随机森林模型训练完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '随机森林模型训练失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行随机森林训练器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
