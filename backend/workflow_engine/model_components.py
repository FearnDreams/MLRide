"""
模型训练组件执行器

该模块实现了模型训练相关的组件执行器，包括各种机器学习算法的训练和预测功能。
"""

import logging
import json
import traceback
from typing import Dict, Any, List
from .executors import BaseComponentExecutor, ExecutionResult
import pandas as pd

logger = logging.getLogger(__name__)

class BaseModelTrainer(BaseComponentExecutor):
    """模型训练器基类
    
    所有模型训练器的基类，提供通用方法。
    """
    
    def _ensure_serializable(self, obj):
        """确保对象可以被序列化为JSON
        
        Args:
            obj: 需要检查的对象
            
        Returns:
            可序列化的对象
        """
        import numpy as np
        import pandas as pd
        
        if isinstance(obj, dict):
            return {k: self._ensure_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return [self._ensure_serializable(item) for item in obj]
        elif isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return self._ensure_serializable(obj.tolist())
        elif obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        elif hasattr(obj, '__class__') and obj.__class__.__module__ != 'builtins':
            # 对于scikit-learn模型和其他复杂对象，创建一个详细表示
            try:
                obj_type = type(obj).__name__
                obj_module = type(obj).__module__
                
                # 检查是否为scikit-learn模型对象
                if obj_module.startswith('sklearn'):
                    # 创建一个包含关键信息的模型表示
                    model_info = {
                        "type": obj_type,
                        "module": obj_module,
                        "model": obj  # 保留原始模型对象
                    }
                    
                    # 如果有get_params方法，添加模型参数
                    if hasattr(obj, 'get_params'):
                        model_info['params'] = self._ensure_serializable(obj.get_params())
                    
                    # 特别处理常见的模型属性
                    if hasattr(obj, 'feature_importances_'):
                        model_info['feature_importances'] = self._ensure_serializable(obj.feature_importances_)
                    
                    if hasattr(obj, 'classes_'):
                        model_info['classes'] = self._ensure_serializable(obj.classes_)
                    
                    if hasattr(obj, 'coef_'):
                        model_info['coefficients'] = self._ensure_serializable(obj.coef_)
                    
                    if hasattr(obj, 'intercept_'):
                        model_info['intercept'] = self._ensure_serializable(obj.intercept_)
                    
                    # 检查是否有预测方法
                    model_info['has_predict'] = hasattr(obj, 'predict')
                    model_info['has_predict_proba'] = hasattr(obj, 'predict_proba')
                    
                    # 特别处理随机森林模型
                    if obj_type in ['RandomForestClassifier', 'RandomForestRegressor']:
                        # 保存树数量
                        if hasattr(obj, 'n_estimators'):
                            model_info['n_estimators'] = obj.n_estimators
                        if hasattr(obj, 'criterion'):
                            model_info['criterion'] = obj.criterion
                        if hasattr(obj, 'max_depth'):
                            model_info['max_depth'] = obj.max_depth
                        if hasattr(obj, 'max_features'):
                            model_info['max_features'] = self._ensure_serializable(obj.max_features)
                        if hasattr(obj, 'bootstrap'):
                            model_info['bootstrap'] = obj.bootstrap
                    
                    return model_info
                else:
                    # 返回对象的简要描述
                    return {
                        "info": {
                            "type": obj_type,
                            "module": obj_module
                        },
                        "message": "数据太大，无法保存到数据库",
                        "truncated": True
                    }
            except Exception as e:
                return {
                    "message": "序列化对象失败",
                    "error": str(e),
                    "type": str(type(obj))
                }
        else:
            # 对于不可序列化的对象，返回其字符串表示
            try:
                return str(obj)
            except:
                return "不可序列化对象"
    
    def select_features(self, train_df, parameters):
        """根据参数选择特征列
        
        Args:
            train_df: 训练数据DataFrame
            parameters: 参数字典
            
        Returns:
            list: 选择的特征列列表
            str: 错误信息（如果有）
        """
        import pandas as pd
        
        target = parameters.get('target', '')
        if not target:
            return [], "未指定目标变量，请在参数中设置'target'"
        
        # 检查目标变量是否存在
        if target not in train_df.columns:
            return [], f"目标变量 '{target}' 不在数据集中"
        
        # 获取特征选择模式
        feature_selection_mode = parameters.get('feature_selection_mode', 'all_numeric')
        
        # 解析特征列参数
        features = parameters.get('features', '')
        if isinstance(features, str) and features:
            features = [f.strip() for f in features.split(',') if f.strip()]
        
        if feature_selection_mode == 'specified':
            # 使用指定的特征列
            if features:
                feature_cols = [col for col in features if col in train_df.columns and col != target]
            else:
                feature_cols = []
            
            if not feature_cols:
                return [], "特征选择模式为'specified'，但未指定有效的特征列"
                
        elif feature_selection_mode == 'exclude_specified':
            # 排除指定的列
            exclude_columns = parameters.get('exclude_columns', '')
            if isinstance(exclude_columns, str) and exclude_columns:
                exclude_cols = [col.strip() for col in exclude_columns.split(',') if col.strip()]
            else:
                exclude_cols = []
            
            # 使用所有数值列，但排除指定的列和目标列
            feature_cols = [col for col in train_df.columns 
                           if col != target 
                           and col not in exclude_cols 
                           and pd.api.types.is_numeric_dtype(train_df[col])]
                           
        elif feature_selection_mode == 'auto_vectorized':
            # 自动选择向量化后的特征列
            vectorized_prefix = parameters.get('vectorized_prefix', 'feature_')
            
            # 获取所有以指定前缀开头的列
            feature_cols = [col for col in train_df.columns 
                           if col.startswith(vectorized_prefix) 
                           and pd.api.types.is_numeric_dtype(train_df[col])]
                           
            if not feature_cols:
                # 如果没有找到以指定前缀开头的列，尝试智能识别可能的向量化特征
                # 策略1：排除非数值列（通常是原始文本）和目标列
                text_cols = []
                for col in train_df.columns:
                    if col != target and not pd.api.types.is_numeric_dtype(train_df[col]):
                        text_cols.append(col)
                
                # 排除文本列和目标列
                feature_cols = [col for col in train_df.columns 
                               if col != target 
                               and col not in text_cols 
                               and pd.api.types.is_numeric_dtype(train_df[col])]
        else:
            # 默认：使用所有数值列作为特征
            feature_cols = [col for col in train_df.columns 
                           if col != target 
                           and pd.api.types.is_numeric_dtype(train_df[col])]
        
        if not feature_cols:
            return [], "没有找到有效的特征列，请检查数据或特征选择参数"
            
        return feature_cols, None
    
    def _prepare_data(self, train_dataset, features, target):
        """准备数据处理通用功能"""
        code = f"""
try:
    import pandas as pd
    import numpy as np
    
    # 解析训练数据集
    train_df = pd.read_json('''{json.dumps(train_dataset.get('data', '{}'))}''', orient='split')
    
    # 检查目标变量是否存在
    if '{target}' not in train_df.columns:
        raise ValueError(f"目标变量 '{target}' 不在数据集中")
    
    # 确定特征列
    feature_selection_mode = parameters.get('feature_selection_mode', 'all_numeric')
    
    if feature_selection_mode == 'specified':
        # 使用指定的特征列
        if features:
            feature_cols = [col for col in features if col in train_df.columns and col != target]
    else:
            feature_cols = []
        
        if not feature_cols:
            return ExecutionResult(
                success=False,
                error_message="特征选择模式为'specified'，但未指定有效的特征列"
            )
            
    elif feature_selection_mode == 'exclude_specified':
        # 排除指定的列
        exclude_columns = parameters.get('exclude_columns', '')
        if isinstance(exclude_columns, str) and exclude_columns:
            exclude_cols = [col.strip() for col in exclude_columns.split(',') if col.strip()]
        else:
            exclude_cols = []
        
        # 使用所有数值列，但排除指定的列和目标列
        feature_cols = [col for col in train_df.columns 
                       if col != target 
                       and col not in exclude_cols 
                       and pd.api.types.is_numeric_dtype(train_df[col])]
                       
    elif feature_selection_mode == 'auto_vectorized':
        # 自动选择向量化后的特征列
        vectorized_prefix = parameters.get('vectorized_prefix', 'feature_')
        
        # 获取所有以指定前缀开头的列
        feature_cols = [col for col in train_df.columns 
                       if col.startswith(vectorized_prefix) 
                       and pd.api.types.is_numeric_dtype(train_df[col])]
                       
        if not feature_cols:
            # 如果没有找到以指定前缀开头的列，尝试智能识别可能的向量化特征
            # 策略1：排除第一列（通常是原始文本）和目标列
            if len(train_df.columns) > 2:
                text_cols = []
                for col in train_df.columns:
                    if col != target and not pd.api.types.is_numeric_dtype(train_df[col]):
                        text_cols.append(col)
                
                # 排除文本列和目标列
                feature_cols = [col for col in train_df.columns 
                               if col != target 
                               and col not in text_cols 
                               and pd.api.types.is_numeric_dtype(train_df[col])]
    else:
        # 默认：使用所有数值列作为特征
        feature_cols = [col for col in train_df.columns 
                       if col != target 
                       and pd.api.types.is_numeric_dtype(train_df[col])]
    
    if not feature_cols:
        raise ValueError("没有有效的特征列")
    
    # 准备特征矩阵和目标变量
    X_train = train_df[feature_cols].values
    y_train = train_df['{target}'].values
    
    # 检查数据有效性
    if np.isnan(X_train).any() or np.isnan(y_train).any():
        raise ValueError("数据集包含NaN值，请先进行数据清洗")
    
    # 获取问题类型（分类或回归）
    if pd.api.types.is_numeric_dtype(train_df['{target}']):
        # 检查目标是否是分类变量
        if len(np.unique(y_train)) < 10 and all(int(y) == y for y in y_train):
            problem_type = 'classification'
        else:
            problem_type = 'regression'
    else:
        problem_type = 'classification'
        # 对分类目标进行标签编码
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        y_train = le.fit_transform(y_train)
        class_names = le.classes_.tolist()
    
    # 返回结果
    result = {{
        'X_train': X_train.tolist(),
        'y_train': y_train.tolist(),
        'feature_cols': feature_cols,
        'problem_type': problem_type,
        'class_names': class_names if problem_type == 'classification' and 'class_names' in locals() else None,
        'label_encoder': le.classes_.tolist() if problem_type == 'classification' and 'le' in locals() else None
    }}
except Exception as e:
    raise Exception(f"准备训练数据失败: {{str(e)}}")
"""
        return code

    def _generate_prediction_code(self, model_type):
        """生成预测代码"""
        return f"""
# 如果提供了测试数据，进行预测
if 'test_df' in locals():
    # 准备测试特征矩阵
    X_test = test_df[feature_cols].values
    
    # 检查测试数据是否有目标变量
    has_target = '{{target}}' in test_df.columns
    
    if has_target:
        y_test = test_df['{{target}}'].values
        if problem_type == 'classification' and 'le' in locals():
            # 对分类目标进行标签编码
            y_test = le.transform(y_test)
    
    # 进行预测
    if problem_type == 'classification':
        # 分类问题获取预测概率
        if hasattr(model, 'predict_proba'):
            y_pred_proba = model.predict_proba(X_test)
            predictions_proba = y_pred_proba.tolist()
        else:
            predictions_proba = None
        
        # 预测类别
        y_pred = model.predict(X_test)
        predictions = y_pred.tolist()
        
        # 如果有标签编码器，将整数标签转回原始类别
        if 'le' in locals():
            original_predictions = le.inverse_transform(y_pred).tolist()
        else:
            original_predictions = predictions
    else:
        # 回归问题
        y_pred = model.predict(X_test)
        predictions = y_pred.tolist()
        predictions_proba = None
        original_predictions = predictions
    
    # 获取测试指标
    if has_target:
        if problem_type == 'classification':
            # 分类指标
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
            
            metrics = {{
                'accuracy': float(accuracy_score(y_test, y_pred)),
                'precision': float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
                'f1': float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
            }}
            
            # 如果有概率预测，计算ROC AUC
            if predictions_proba is not None and len(np.unique(y_test)) == 2:
                metrics['roc_auc'] = float(roc_auc_score(y_test, y_pred_proba[:, 1]))
        else:
            # 回归指标
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            
            metrics = {{
                'mse': float(mean_squared_error(y_test, y_pred)),
                'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred))),
                'mae': float(mean_absolute_error(y_test, y_pred)),
                'r2': float(r2_score(y_test, y_pred))
            }}
    else:
        metrics = None
    
    # 准备预测结果数据框
    predictions_df = test_df.copy()
    predictions_df['prediction'] = original_predictions
    
    # 如果有概率预测，添加到数据框
    if predictions_proba is not None and problem_type == 'classification':
        if len(np.unique(y_train)) == 2:
            predictions_df['probability'] = y_pred_proba[:, 1]
        else:
            for i, class_name in enumerate(class_names if 'class_names' in locals() else range(y_pred_proba.shape[1])):
                predictions_df[f'prob_{{class_name}}'] = y_pred_proba[:, i]
    
    # 设置预测结果
    test_results = {{
        'predictions': predictions,
        'probabilities': predictions_proba,
        'metrics': metrics,
        'predictions_df': predictions_df.to_json(orient='split')
    }}
else:
    test_results = None
"""

    def _prepare_test_data(self, test_dataset, features, target):
        """准备测试数据处理代码"""
        if not test_dataset:
            return ""
            
        return f"""
# 解析测试数据集
test_df = pd.read_json('''{json.dumps(test_dataset.get('data', '{}'))}''', orient='split')
"""


class LogisticRegressionTrainer(BaseModelTrainer):
    """逻辑回归训练器
    
    训练逻辑回归模型，用于分类任务。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        训练逻辑回归模型
        
        Args:
            inputs: 输入数据，包括:
                - train/train_dataset: 训练数据集
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标变量
                - C: 正则化强度的倒数
                - max_iter: 最大迭代次数
                - solver: 优化算法（'lbfgs', 'newton-cg', 'liblinear', 'sag', 'saga'）
                - penalty: 正则化类型（'l1', 'l2', 'elasticnet', 'none'）
                - multi_class: 多分类方法（'auto', 'ovr', 'multinomial'）
                - random_state: 随机种子
                
        Returns:
            ExecutionResult: 执行结果，包含训练好的模型
        """
        try:
            # 获取输入数据（仅处理train输入）
            train_data = None
            if 'train' in inputs:
                train_data = inputs['train']
            elif 'train_dataset' in inputs:
                train_data = inputs['train_dataset']
            else:
                return ExecutionResult(
                    success=False,
                    error_message="缺少训练数据集，请连接数据源到'train'输入端口"
                )
            
            # 解析参数
            features = parameters.get('features', '')
            if isinstance(features, str) and features:
                features = [f.strip() for f in features.split(',') if f.strip()]
            
            target = parameters.get('target', '')
            if not target:
                return ExecutionResult(
                    success=False,
                    error_message="未指定目标变量，请在参数中设置'target'"
                )
            
            # 获取其他参数并确保类型正确
            # 更健壮的C参数处理
            C_param = parameters.get('C', 1.0)
            if isinstance(C_param, str):
                try:
                    C = float(C_param)
                except ValueError:
                    C = 1.0  # 默认值
            else:
                C = float(C_param) if C_param is not None else 1.0
                
            # 更健壮的max_iter参数处理
            max_iter_param = parameters.get('max_iter', 1000)
            if isinstance(max_iter_param, str):
                try:
                    max_iter = int(max_iter_param)
                except ValueError:
                    max_iter = 1000  # 默认值
            else:
                max_iter = int(max_iter_param) if max_iter_param is not None else 1000
                
            solver = parameters.get('solver', 'lbfgs')
            penalty = parameters.get('penalty', 'l2')
            multi_class = parameters.get('multi_class', 'auto')
            
            # 更健壮的random_state参数处理
            random_state_param = parameters.get('random_state', 42)
            if isinstance(random_state_param, str):
                try:
                    random_state = int(random_state_param)
                except ValueError:
                    random_state = 42  # 默认值
            else:
                random_state = int(random_state_param) if random_state_param is not None else 42
            
            # 直接使用Python代码处理数据和训练模型
            import pandas as pd
            import numpy as np
            import json
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import LabelEncoder
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            
            # 解析数据
            if isinstance(train_data, dict) and 'data' in train_data:
                # 根据数据类型进行不同处理
                if isinstance(train_data['data'], str):
                    # 如果数据已经是字符串（JSON字符串），直接解析
                    from io import StringIO
                    train_df = pd.read_json(StringIO(train_data['data']), orient='split')
                elif isinstance(train_data['data'], dict):
                    # 如果是字典，转换为JSON字符串
                    from io import StringIO
                    train_df = pd.read_json(StringIO(json.dumps(train_data['data'])), orient='split')
                else:
                    # 尝试直接使用data字段
                    train_df = pd.DataFrame(train_data['data'])
            else:
                logger.error(f"无法解析训练数据：{train_data}")
                return ExecutionResult(
                    success=False,
                    error_message="无法解析训练数据，请检查上游组件输出"
                )
            
            # 使用通用方法选择特征列
            feature_cols, error_message = self.select_features(train_df, parameters)
            if error_message:
                return ExecutionResult(
                    success=False,
                    error_message=error_message
                )
            
            # 获取目标变量名
            target = parameters.get('target', '')
            
            # 准备训练数据
            X_train = train_df[feature_cols].values
            y_train = train_df[target].values
            
            # 检查数据有效性
            if np.isnan(X_train).any() or np.isnan(y_train).any():
                return ExecutionResult(
                    success=False,
                    error_message="数据集包含NaN值，请先进行数据清洗"
                )
            
            # 处理非数值目标变量
            label_encoder = None
            classes_mapping = None
            
            if not pd.api.types.is_numeric_dtype(train_df[target]):
                # 对分类目标进行标签编码
                label_encoder = LabelEncoder()
                y_train = label_encoder.fit_transform(y_train)
                classes_mapping = dict(zip(label_encoder.classes_, range(len(label_encoder.classes_))))
            
            # 创建并训练模型
            model = LogisticRegression(
                C=C, 
                max_iter=max_iter,
                solver=solver,
                penalty=penalty,
                multi_class=multi_class,
                random_state=random_state
            )
            
            model.fit(X_train, y_train)

            # 获取模型参数
            if hasattr(model, 'coef_'):
                if model.coef_.shape[0] == 1:
                    # 二分类问题
                    coefficients = model.coef_[0].tolist()
                else:
                    # 多分类问题
                    coefficients = model.coef_.tolist()
            else:
                coefficients = []
                
            intercept = model.intercept_.tolist() if hasattr(model, 'intercept_') else []
            
            # 计算训练指标
            y_train_pred = model.predict(X_train)
            train_metrics = {
                'accuracy': float(accuracy_score(y_train, y_train_pred)),
                'precision': float(precision_score(y_train, y_train_pred, average='weighted', zero_division=0)),
                'recall': float(recall_score(y_train, y_train_pred, average='weighted', zero_division=0)),
                'f1': float(f1_score(y_train, y_train_pred, average='weighted', zero_division=0))
            }
            
            # 计算特征重要性
            feature_importance = {}
            if hasattr(model, 'coef_'):
                if model.coef_.shape[0] > 1:
                    # 多分类，取绝对值的平均
                    for i, feat in enumerate(feature_cols):
                        if i < model.coef_[0].shape[0]:
                            importance = np.mean([abs(class_coef[i]) for class_coef in model.coef_])
                        feature_importance[feat] = float(importance)
                else:
                    # 二分类
                    for i, feat in enumerate(feature_cols):
                        if i < len(coefficients):
                            importance = abs(coefficients[i])
                        feature_importance[feat] = float(importance)

            # 模型信息
            model_info = {
                'type': 'logistic_regression',
                'coefficients': coefficients,
                'intercept': intercept,
                'feature_names': feature_cols,
                'target': target,
                'classes': model.classes_.tolist() if hasattr(model, 'classes_') else [],
                'classes_mapping': classes_mapping,
                'model': model
            }
            
            # 准备输出数据
            outputs = {
                'model': model_info,
                'train_metrics': train_metrics,
                'feature_importance': feature_importance
            }
            
            # 确保输出可序列化
            outputs = self._ensure_serializable(outputs)
            
            # 返回模型和训练相关信息
            return ExecutionResult(
                success=True,
                outputs=outputs,
                logs=["逻辑回归模型训练完成"]
            )
                
        except Exception as e:
            logger.error(f"执行逻辑回归训练器时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return ExecutionResult(
                success=False,
                error_message=str(e),
                logs=[traceback.format_exc()]
            )


class RandomForestTrainer(BaseModelTrainer):
    """随机森林训练器
    
    训练随机森林模型，可用于分类和回归任务。
    对应前端组件ID: random-forest
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        训练随机森林模型
        
        Args:
            inputs: 输入数据，包括:
                - train/train_dataset: 训练数据集
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标变量
                - task_type: 任务类型（classification/regression）
                - n_estimators: 树的数量
                - criterion: 切分标准（gini/entropy/squared_error/absolute_error）
                - max_depth: 最大深度
                - max_features: 最大特征数（sqrt/log2/auto）
                - bootstrap: 是否使用自助采样
                - random_state: 随机种子
                
        Returns:
            ExecutionResult: 执行结果，包含训练好的模型和预测结果
        """
        try:
            # 获取输入数据（仅处理train输入）
            train_data = None
            if 'train' in inputs:
                train_data = inputs['train']
            elif 'train_dataset' in inputs:
                train_data = inputs['train_dataset']
            else:
                return ExecutionResult(
                    success=False,
                    error_message="缺少训练数据集，请连接数据源到'train'输入端口"
                )
            
            # 解析参数
            features = parameters.get('features', '')
            if isinstance(features, str) and features:
                features = [f.strip() for f in features.split(',') if f.strip()]
            
            target = parameters.get('target', '')
            if not target:
                return ExecutionResult(
                    success=False,
                    error_message="未指定目标变量，请在参数中设置'target'"
                )
            
            # 获取其他参数并确保类型正确
            task_type = parameters.get('task_type', 'classification')
            n_estimators = int(parameters.get('n_estimators', 100))
            criterion = parameters.get('criterion', 'gini' if task_type == 'classification' else 'squared_error')
            
            # 更健壮的max_depth参数处理
            max_depth = parameters.get('max_depth')
            if max_depth is not None:
                if isinstance(max_depth, str):
                    if max_depth.lower() == 'none':
                        max_depth = None
                    else:
                        try:
                            max_depth = int(max_depth)
                        except ValueError:
                            max_depth = None
                # 已经是整数类型，不需要转换
                elif not isinstance(max_depth, int):
                    try:
                        max_depth = int(max_depth)
                    except (ValueError, TypeError):
                        max_depth = None
            
            max_features = parameters.get('max_features', 'sqrt')
            bootstrap = parameters.get('bootstrap', True)
            if isinstance(bootstrap, str):
                bootstrap = bootstrap.lower() == 'true'
                
            # 更健壮的random_state参数处理
            random_state_param = parameters.get('random_state', 42)
            if isinstance(random_state_param, str):
                try:
                    random_state = int(random_state_param)
                except ValueError:
                    random_state = 42  # 默认值
            else:
                random_state = int(random_state_param) if random_state_param is not None else 42
            
            # 直接使用Python代码处理数据和训练模型
            import pandas as pd
            import numpy as np
            import json
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            from sklearn.preprocessing import LabelEncoder
            
            # 解析数据
            if isinstance(train_data, dict) and 'data' in train_data:
                # 根据数据类型进行不同处理
                if isinstance(train_data['data'], str):
                    # 如果数据已经是字符串（JSON字符串），直接解析
                    from io import StringIO
                    train_df = pd.read_json(StringIO(train_data['data']), orient='split')
                elif isinstance(train_data['data'], dict):
                    # 如果是字典，转换为JSON字符串
                    from io import StringIO
                    train_df = pd.read_json(StringIO(json.dumps(train_data['data'])), orient='split')
                else:
                    # 尝试直接使用data字段
                    train_df = pd.DataFrame(train_data['data'])
            else:
                logger.error(f"无法解析训练数据：{train_data}")
                return ExecutionResult(
                    success=False,
                    error_message="无法解析训练数据，请检查上游组件输出"
                )
            
            # 使用通用方法选择特征列
            feature_cols, error_message = self.select_features(train_df, parameters)
            if error_message:
                return ExecutionResult(
                    success=False,
                    error_message=error_message
                )
            
            # 获取目标变量名
            target = parameters.get('target', '')
            
            # 准备训练数据
            X_train = train_df[feature_cols].values
            y_train = train_df[target].values
            
            # 检查数据有效性
            if np.isnan(X_train).any() or np.isnan(y_train).any():
                return ExecutionResult(
                    success=False,
                    error_message="数据集包含NaN值，请先进行数据清洗"
                )
            
            # 处理非数值目标变量（分类任务）
            label_encoder = None
            if task_type == 'classification' and not pd.api.types.is_numeric_dtype(train_df[target]):
                label_encoder = LabelEncoder()
                y_train = label_encoder.fit_transform(y_train)
            
            # 根据任务类型创建并训练模型
            if task_type == 'classification':
                model = RandomForestClassifier(
                    n_estimators=n_estimators,
                    criterion=criterion,
                    max_depth=max_depth,
                    max_features=max_features,
                    bootstrap=bootstrap,
                    random_state=random_state,
                    n_jobs=-1  # 使用所有CPU核心
                )
            else:  # 回归
                model = RandomForestRegressor(
                    n_estimators=n_estimators,
                    criterion=criterion,
                    max_depth=max_depth,
                    max_features=max_features,
                    bootstrap=bootstrap,
                    random_state=random_state,
                    n_jobs=-1  # 使用所有CPU核心
                )
            
            # 训练模型
            model.fit(X_train, y_train)
            
            # 获取特征重要性
            feature_importances = model.feature_importances_.tolist()
            
            # 计算训练指标和准备输出
            y_train_pred = model.predict(X_train)
            
            if task_type == 'classification':
                # 分类指标
                train_metrics = {
                    'accuracy': float(accuracy_score(y_train, y_train_pred)),
                    'precision': float(precision_score(y_train, y_train_pred, average='weighted', zero_division=0)),
                    'recall': float(recall_score(y_train, y_train_pred, average='weighted', zero_division=0)),
                    'f1': float(f1_score(y_train, y_train_pred, average='weighted', zero_division=0))
                }
                
                # 模型信息
                classes = model.classes_.tolist()
                if label_encoder is not None:
                    original_classes = label_encoder.classes_.tolist()
                else:
                    original_classes = classes
                
                model_info = {
                    'type': 'random_forest',
                    'subtype': 'classification',
                    'n_estimators': n_estimators,
                    'criterion': criterion,
                    'max_depth': max_depth,
                    'max_features': max_features,
                    'bootstrap': bootstrap,
                    'feature_names': feature_cols,
                    'target': target,
                    'classes': original_classes,
                    'model': model
                }
            else:  # 回归
                # 回归指标
                train_metrics = {
                    'mse': float(mean_squared_error(y_train, y_train_pred)),
                    'rmse': float(np.sqrt(mean_squared_error(y_train, y_train_pred))),
                    'mae': float(mean_absolute_error(y_train, y_train_pred)),
                    'r2': float(r2_score(y_train, y_train_pred))
                }
                
                # 模型信息
                model_info = {
                    'type': 'random_forest',
                    'subtype': 'regression',
                    'n_estimators': n_estimators,
                    'criterion': criterion,
                    'max_depth': max_depth,
                    'max_features': max_features,
                    'bootstrap': bootstrap,
                    'feature_names': feature_cols,
                    'target': target
                }
            
            # 计算特征重要性
            feature_importance = {}
            for i, feat in enumerate(feature_cols):
                if i < len(feature_importances):
                    feature_importance[feat] = float(feature_importances[i])
            
            # 准备输出数据
            outputs = {
                'model': model_info,
                'train_metrics': train_metrics,
                'feature_importance': feature_importance
            }
            
            # 确保输出可序列化
            outputs = self._ensure_serializable(outputs)
            
            # 返回模型和训练相关信息
            return ExecutionResult(
                success=True,
                outputs=outputs,
                logs=[f"随机森林({task_type})模型训练完成，树的数量: {n_estimators}"]
            )
                
        except Exception as e:
            logger.error(f"执行随机森林训练器时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return ExecutionResult(
                success=False,
                error_message=str(e),
                logs=[traceback.format_exc()]
            )

