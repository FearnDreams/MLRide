"""
模型训练组件执行器

该模块实现了模型训练相关的组件执行器，包括各种机器学习算法的训练和预测功能。
"""

import logging
import json
import traceback
from typing import Dict, Any, List
from .executors import BaseComponentExecutor, ExecutionResult

logger = logging.getLogger(__name__)

class BaseModelTrainer(BaseComponentExecutor):
    """模型训练器基类
    
    所有模型训练器的基类，提供通用方法。
    """
    
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
    if {repr(features)}:
        feature_cols = [col for col in {repr(features)} if col in train_df.columns and col != '{target}']
    else:
        # 使用除目标变量外的所有列作为特征
        feature_cols = [col for col in train_df.columns if col != '{target}' and pd.api.types.is_numeric_dtype(train_df[col])]
    
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
    has_target = '{target}' in test_df.columns
    
    if has_target:
        y_test = test_df['{target}'].values
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
                predictions_df[f'prob_{class_name}'] = y_pred_proba[:, i]
    
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


class LinearRegressionTrainer(BaseModelTrainer):
    """线性回归训练器
    
    训练线性回归模型，用于预测连续型目标变量。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        训练线性回归模型
        
        Args:
            inputs: 输入数据，包括:
                - train_dataset: 训练数据集
                - test_dataset: 测试数据集（可选）
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标变量
                - fit_intercept: 是否拟合截距
                
        Returns:
            ExecutionResult: 执行结果，包含训练好的模型和预测结果
        """
        try:
            # 获取输入数据
            if 'train_dataset' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少训练数据集"
                )
            
            train_dataset = inputs['train_dataset']
            test_dataset = inputs.get('test_dataset')
            
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
            
            fit_intercept = parameters.get('fit_intercept', 'true') == 'true'
            
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
# 训练线性回归模型
from sklearn.linear_model import LinearRegression

model = LinearRegression(fit_intercept={fit_intercept})
model.fit(X_train, y_train)

# 获取模型参数
coefficients = model.coef_.tolist()
intercept = float(model.intercept_)

# 计算训练集预测值和指标
y_train_pred = model.predict(X_train)
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

train_metrics = {{
    'mse': float(mean_squared_error(y_train, y_train_pred)),
    'rmse': float(np.sqrt(mean_squared_error(y_train, y_train_pred))),
    'mae': float(mean_absolute_error(y_train, y_train_pred)),
    'r2': float(r2_score(y_train, y_train_pred))
}}

# 模型对象信息
model_info = {{
    'type': 'linear_regression',
    'coefficients': coefficients,
    'intercept': intercept,
    'feature_names': feature_cols,
    'target': '{target}'
}}
"""
            
            # 添加预测代码
            prediction_code = self._generate_prediction_code('linear_regression')
            
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
    'feature_importance': {{feat: abs(coef) for feat, coef in zip(feature_cols, coefficients)}}
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
                    logs=["线性回归模型训练完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '线性回归模型训练失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行线性回归训练器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class LogisticRegressionTrainer(BaseModelTrainer):
    """逻辑回归训练器
    
    训练逻辑回归模型，用于分类任务。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        训练逻辑回归模型
        
        Args:
            inputs: 输入数据，包括:
                - train_dataset: 训练数据集
                - test_dataset: 测试数据集（可选）
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标变量
                - C: 正则化强度的倒数
                - max_iter: 最大迭代次数
                
        Returns:
            ExecutionResult: 执行结果，包含训练好的模型和预测结果
        """
        try:
            # 获取输入数据
            if 'train_dataset' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少训练数据集"
                )
            
            train_dataset = inputs['train_dataset']
            test_dataset = inputs.get('test_dataset')
            
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
            
            C = float(parameters.get('C', 1.0))
            max_iter = int(parameters.get('max_iter', 100))
            
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
# 训练逻辑回归模型
from sklearn.linear_model import LogisticRegression

model = LogisticRegression(C={C}, max_iter={max_iter}, random_state=42)
model.fit(X_train, y_train)

# 获取模型参数
if model.coef_.shape[0] == 1:
    # 二分类问题
    coefficients = model.coef_[0].tolist()
else:
    # 多分类问题
    coefficients = model.coef_.tolist()
    
intercept = model.intercept_.tolist()

# 计算训练集预测值和指标
y_train_pred = model.predict(X_train)
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

train_metrics = {{
    'accuracy': float(accuracy_score(y_train, y_train_pred)),
    'precision': float(precision_score(y_train, y_train_pred, average='weighted', zero_division=0)),
    'recall': float(recall_score(y_train, y_train_pred, average='weighted', zero_division=0)),
    'f1': float(f1_score(y_train, y_train_pred, average='weighted', zero_division=0))
}}

# 模型对象信息
model_info = {{
    'type': 'logistic_regression',
    'coefficients': coefficients,
    'intercept': intercept,
    'feature_names': feature_cols,
    'target': '{target}',
    'classes': model.classes_.tolist()
}}
"""
            
            # 添加预测代码
            prediction_code = self._generate_prediction_code('logistic_regression')
            
            # 组合所有代码
            code = f"""
{data_prep_code}
{test_data_code}
{model_code}
{prediction_code}

# 计算特征重要性
if isinstance(coefficients[0], list):
    # 多分类，取绝对值的平均
    feature_importance = {{feat: np.mean([abs(class_coef[i]) for class_coef in coefficients]) 
                          for i, feat in enumerate(feature_cols)}}
else:
    # 二分类
    feature_importance = {{feat: abs(coef) for feat, coef in zip(feature_cols, coefficients)}}

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
                    logs=["逻辑回归模型训练完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '逻辑回归模型训练失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行逻辑回归训练器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class SVMTrainer(BaseModelTrainer):
    """支持向量机训练器
    
    训练支持向量机模型，可用于分类和回归任务。
    对应前端组件ID: svm
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        训练支持向量机模型
        
        Args:
            inputs: 输入数据，包括:
                - train: 训练数据集
                - test: 测试数据集（可选）
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标变量
                - task_type: 任务类型（classification/regression）
                - kernel: 核函数类型（linear/poly/rbf/sigmoid）
                - C: 正则化参数
                - gamma: gamma参数
                - degree: 多项式核的次数
                - probability: 是否启用概率估计
                - random_state: 随机种子
                
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
            
            train_dataset = inputs.get('train', {})
            test_dataset = inputs.get('test', {})
            
            # 获取参数
            features = parameters.get('features', '')
            target = parameters.get('target', '')
            task_type = parameters.get('task_type', 'classification')
            kernel = parameters.get('kernel', 'rbf')
            C = float(parameters.get('C', 1.0))
            gamma = parameters.get('gamma', 'scale')
            degree = int(parameters.get('degree', 3))
            probability = bool(parameters.get('probability', True))
            random_state = int(parameters.get('random_state', 42))
            
            # 检查参数
            if not target:
                return ExecutionResult(
                    success=False,
                    error_message="缺少目标变量参数"
                )
                
            # 如果特征是字符串，分割为列表
            if isinstance(features, str) and features:
                features = [f.strip() for f in features.split(',') if f.strip()]
            
            # 准备数据处理代码
            data_prep_code = self._prepare_data(train_dataset, features, target)
            
            # 准备测试数据代码
            test_data_code = self._prepare_test_data(test_dataset, features, target)
            
            # 模型训练代码
            model_code = f"""
# 选择模型类型
from sklearn.svm import SVC, SVR
import pickle
import base64
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# 根据任务类型选择模型
if '{task_type}' == 'classification':
    # 创建模型
    model = SVC(
        C={C}, 
        kernel='{kernel}', 
        degree={degree}, 
        gamma='{gamma}',
        probability={str(probability).lower()},
        random_state={random_state}
    )
    
    # 训练模型
    model.fit(X_train, y_train)
    
    # 获取模型参数
    if model.kernel == 'linear' and hasattr(model, 'coef_'):
        coefficients = model.coef_.tolist()
        intercept = model.intercept_.tolist()
    else:
        # 对于非线性核，无法直接获取系数
        coefficients = []
        intercept = model.intercept_.tolist() if hasattr(model, 'intercept_') else []
    
    # 保存模型
    model_bytes = pickle.dumps(model)
    model_data = base64.b16encode(model_bytes).decode('utf-8')
    
    # 在训练集上进行预测
    y_train_pred = model.predict(X_train)
    
    # 计算训练指标
    train_metrics = {{
        'accuracy': float(accuracy_score(y_train, y_train_pred)),
        'precision': float(precision_score(y_train, y_train_pred, average='weighted', zero_division=0)),
        'recall': float(recall_score(y_train, y_train_pred, average='weighted', zero_division=0)),
        'f1': float(f1_score(y_train, y_train_pred, average='weighted', zero_division=0))
    }}
    
    # 模型对象信息
    model_info = {{
        'type': 'svm',
        'subtype': 'classification',
        'kernel': '{kernel}',
        'n_support': model.n_support_.tolist(),
        'support_vectors_count': len(model.support_),
        'feature_names': feature_cols,
        'target': '{target}',
        'classes': model.classes_.tolist(),
        'model_data': model_data
    }}
else:  # 回归模型
    # 创建模型
    model = SVR(
        C={C}, 
        kernel='{kernel}', 
        degree={degree}, 
        gamma='{gamma}',
        epsilon=0.1
    )
    
    # 训练模型
    model.fit(X_train, y_train)
    
    # 获取模型参数
    if model.kernel == 'linear' and hasattr(model, 'coef_'):
        coefficients = model.coef_.tolist()
        intercept = model.intercept_.tolist() if hasattr(model, 'intercept_') else []
    else:
        # 对于非线性核，无法直接获取系数
        coefficients = []
        intercept = model.intercept_ if hasattr(model, 'intercept_') else 0.0
    
    # 保存模型
    model_bytes = pickle.dumps(model)
    model_data = base64.b16encode(model_bytes).decode('utf-8')
    
    # 在训练集上进行预测
    y_train_pred = model.predict(X_train)
    
    # 计算训练指标
    train_metrics = {{
        'mse': float(mean_squared_error(y_train, y_train_pred)),
        'rmse': float(mean_squared_error(y_train, y_train_pred, squared=False)),
        'mae': float(mean_absolute_error(y_train, y_train_pred)),
        'r2': float(r2_score(y_train, y_train_pred))
    }}
    
    # 模型对象信息
    model_info = {{
        'type': 'svm',
        'subtype': 'regression',
        'kernel': '{kernel}',
        'n_support': model.n_support_.tolist() if hasattr(model, 'n_support_') else [],
        'support_vectors_count': len(model.support_),
        'feature_names': feature_cols,
        'target': '{target}',
        'model_data': model_data
    }}
"""
            
            # 添加预测代码
            prediction_code = """
# 准备结果字典
result = {
    'model_info': model_info,
    'train_metrics': train_metrics
}

# 添加测试集评估结果
if 'X_test' in locals() and 'y_test' in locals():
    test_results = {}
    
    # 在测试集上进行预测
    y_test_pred = model.predict(X_test)
    
    # 获取测试集结果
    if '{task_type}' == 'classification':
        # 如果启用了概率预测
        if {probability} and hasattr(model, 'predict_proba'):
            y_test_proba = model.predict_proba(X_test).tolist()
            test_results['probabilities'] = y_test_proba
        
        # 计算测试指标
        test_results['predictions'] = y_test_pred.tolist()
        test_results['actual'] = y_test.tolist()
        test_results['accuracy'] = float(accuracy_score(y_test, y_test_pred))
        test_results['precision'] = float(precision_score(y_test, y_test_pred, average='weighted', zero_division=0))
        test_results['recall'] = float(recall_score(y_test, y_test_pred, average='weighted', zero_division=0))
        test_results['f1'] = float(f1_score(y_test, y_test_pred, average='weighted', zero_division=0))
    else:
        # 回归指标
        test_results['predictions'] = y_test_pred.tolist()
        test_results['actual'] = y_test.tolist()
        test_results['mse'] = float(mean_squared_error(y_test, y_test_pred))
        test_results['rmse'] = float(mean_squared_error(y_test, y_test_pred, squared=False))
        test_results['mae'] = float(mean_absolute_error(y_test, y_test_pred))
        test_results['r2'] = float(r2_score(y_test, y_test_pred))
    
    result['test_results'] = test_results

# 计算特征重要性（仅适用于线性核）
feature_importance = {}
if model.kernel == 'linear' and hasattr(model, 'coef_'):
    if '{task_type}' == 'classification' and len(model.classes_) > 2:
        # 多分类情况下，取各类别绝对值的平均
        for i, feat in enumerate(feature_cols):
            importance = np.mean([abs(coef[i]) for coef in coefficients]) if i < len(coefficients[0]) else 0
            feature_importance[feat] = float(importance)
    else:
        # 二分类或回归
        for i, feat in enumerate(feature_cols):
            importance = abs(coefficients[0][i]) if i < len(coefficients[0]) else 0
            feature_importance[feat] = float(importance)
else:
    # 非线性核无法计算特征重要性，使用随机森林估计
    try:
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        
        if '{task_type}' == 'classification':
            rf = RandomForestClassifier(n_estimators=50, random_state=42)
        else:
            rf = RandomForestRegressor(n_estimators=50, random_state=42)
        
        rf.fit(X_train, y_train)
        importances = rf.feature_importances_
        for i, feat in enumerate(feature_cols):
            feature_importance[feat] = float(importances[i])
    except:
        # 如果随机森林失败，使用均匀分布
        for i, feat in enumerate(feature_cols):
            feature_importance[feat] = 1.0 / len(feature_cols)

result['feature_importance'] = feature_importance

print(json.dumps(result))
"""
            
            # 将参数替换到预测代码中
            prediction_code = prediction_code.format(
                task_type=task_type,
                probability=str(probability).lower()
            )
            
            # 组合所有代码
            code = f"""
{data_prep_code}
{test_data_code}
{model_code}
{prediction_code}
"""
            
            # 在容器中执行
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"SVM模型训练失败: {output}"
                )
                
            # 解析输出
            try:
                result = json.loads(output)
                
                return ExecutionResult(
                    success=True,
                    output={
                        'model': result.get('model_info', {}),
                        'train_metrics': result.get('train_metrics', {}),
                        'test_results': result.get('test_results', {}),
                        'feature_importance': result.get('feature_importance', {})
                    }
                )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error_message=f"解析SVM模型结果失败: {str(e)}\n输出: {output}"
                )
            
        except Exception as e:
            error_message = f"执行SVM训练器出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )


class GradientBoostingTrainer(BaseModelTrainer):
    """梯度提升树训练器
    
    训练梯度提升树模型，可用于分类和回归任务。
    对应前端组件ID: gradient-boosting
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        训练梯度提升树模型
        
        Args:
            inputs: 输入数据，包括:
                - train: 训练数据集
                - test: 测试数据集（可选）
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标变量
                - task_type: 任务类型（classification/regression）
                - n_estimators: 树的数量
                - learning_rate: 学习率
                - max_depth: 最大深度
                - subsample: 子样本比例
                - random_state: 随机种子
                
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
            
            train_dataset = inputs.get('train', {})
            test_dataset = inputs.get('test', {})
            
            # 获取参数
            features = parameters.get('features', '')
            target = parameters.get('target', '')
            task_type = parameters.get('task_type', 'classification')
            n_estimators = int(parameters.get('n_estimators', 100))
            learning_rate = float(parameters.get('learning_rate', 0.1))
            max_depth = int(parameters.get('max_depth', 3))
            subsample = float(parameters.get('subsample', 1.0))
            random_state = int(parameters.get('random_state', 42))
            
            # 检查参数
            if not target:
                return ExecutionResult(
                    success=False,
                    error_message="缺少目标变量参数"
                )
                
            # 如果特征是字符串，分割为列表
            if isinstance(features, str) and features:
                features = [f.strip() for f in features.split(',') if f.strip()]
            
            # 准备数据处理代码
            data_prep_code = self._prepare_data(train_dataset, features, target)
            
            # 准备测试数据代码
            test_data_code = self._prepare_test_data(test_dataset, features, target)
            
            # 模型训练代码
            model_code = f"""
# 选择模型类型
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
import pickle
import base64
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# 根据任务类型选择模型
if '{task_type}' == 'classification':
    # 创建模型
    model = GradientBoostingClassifier(
        n_estimators={n_estimators}, 
        learning_rate={learning_rate}, 
        max_depth={max_depth}, 
        subsample={subsample},
        random_state={random_state}
    )
    
    # 训练模型
    model.fit(X_train, y_train)
    
    # 获取特征重要性
    feature_importances = model.feature_importances_
    
    # 保存模型
    model_bytes = pickle.dumps(model)
    model_data = base64.b16encode(model_bytes).decode('utf-8')
    
    # 在训练集上进行预测
    y_train_pred = model.predict(X_train)
    
    # 计算训练指标
    train_metrics = {{
        'accuracy': float(accuracy_score(y_train, y_train_pred)),
        'precision': float(precision_score(y_train, y_train_pred, average='weighted', zero_division=0)),
        'recall': float(recall_score(y_train, y_train_pred, average='weighted', zero_division=0)),
        'f1': float(f1_score(y_train, y_train_pred, average='weighted', zero_division=0))
    }}
    
    # 模型对象信息
    model_info = {{
        'type': 'gradient_boosting',
        'subtype': 'classification',
        'n_estimators': {n_estimators},
        'learning_rate': {learning_rate},
        'max_depth': {max_depth},
        'subsample': {subsample},
        'feature_names': feature_cols,
        'target': '{target}',
        'classes': model.classes_.tolist(),
        'model_data': model_data
    }}
else:  # 回归模型
    # 创建模型
    model = GradientBoostingRegressor(
        n_estimators={n_estimators}, 
        learning_rate={learning_rate}, 
        max_depth={max_depth}, 
        subsample={subsample},
        random_state={random_state}
    )
    
    # 训练模型
    model.fit(X_train, y_train)
    
    # 获取特征重要性
    feature_importances = model.feature_importances_
    
    # 保存模型
    model_bytes = pickle.dumps(model)
    model_data = base64.b16encode(model_bytes).decode('utf-8')
    
    # 在训练集上进行预测
    y_train_pred = model.predict(X_train)
    
    # 计算训练指标
    train_metrics = {{
        'mse': float(mean_squared_error(y_train, y_train_pred)),
        'rmse': float(mean_squared_error(y_train, y_train_pred, squared=False)),
        'mae': float(mean_absolute_error(y_train, y_train_pred)),
        'r2': float(r2_score(y_train, y_train_pred))
    }}
    
    # 模型对象信息
    model_info = {{
        'type': 'gradient_boosting',
        'subtype': 'regression',
        'n_estimators': {n_estimators},
        'learning_rate': {learning_rate},
        'max_depth': {max_depth},
        'subsample': {subsample},
        'feature_names': feature_cols,
        'target': '{target}',
        'model_data': model_data
    }}
"""
            
            # 添加预测代码
            prediction_code = """
# 准备结果字典
result = {
    'model_info': model_info,
    'train_metrics': train_metrics
}

# 添加测试集评估结果
if 'X_test' in locals() and 'y_test' in locals():
    test_results = {}
    
    # 在测试集上进行预测
    y_test_pred = model.predict(X_test)
    
    # 获取测试集结果
    if '{task_type}' == 'classification':
        # 如果存在概率预测方法
        if hasattr(model, 'predict_proba'):
            y_test_proba = model.predict_proba(X_test).tolist()
            test_results['probabilities'] = y_test_proba
        
        # 计算测试指标
        test_results['predictions'] = y_test_pred.tolist()
        test_results['actual'] = y_test.tolist()
        test_results['accuracy'] = float(accuracy_score(y_test, y_test_pred))
        test_results['precision'] = float(precision_score(y_test, y_test_pred, average='weighted', zero_division=0))
        test_results['recall'] = float(recall_score(y_test, y_test_pred, average='weighted', zero_division=0))
        test_results['f1'] = float(f1_score(y_test, y_test_pred, average='weighted', zero_division=0))
    else:
        # 回归指标
        test_results['predictions'] = y_test_pred.tolist()
        test_results['actual'] = y_test.tolist()
        test_results['mse'] = float(mean_squared_error(y_test, y_test_pred))
        test_results['rmse'] = float(mean_squared_error(y_test, y_test_pred, squared=False))
        test_results['mae'] = float(mean_absolute_error(y_test, y_test_pred))
        test_results['r2'] = float(r2_score(y_test, y_test_pred))
    
    result['test_results'] = test_results

# 计算特征重要性
feature_importance = {}
for i, feat in enumerate(feature_cols):
    feature_importance[feat] = float(feature_importances[i])

result['feature_importance'] = feature_importance

print(json.dumps(result))
"""
            
            # 将参数替换到预测代码中
            prediction_code = prediction_code.format(
                task_type=task_type
            )
            
            # 组合所有代码
            code = f"""
{data_prep_code}
{test_data_code}
{model_code}
{prediction_code}
"""
            
            # 在容器中执行
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"梯度提升树模型训练失败: {output}"
                )
                
            # 解析输出
            try:
                result = json.loads(output)
                
                return ExecutionResult(
                    success=True,
                    output={
                        'model': result.get('model_info', {}),
                        'train_metrics': result.get('train_metrics', {}),
                        'test_results': result.get('test_results', {}),
                        'feature_importance': result.get('feature_importance', {})
                    }
                )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error_message=f"解析梯度提升树模型结果失败: {str(e)}\n输出: {output}"
                )
            
        except Exception as e:
            error_message = f"执行梯度提升树训练器出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )


class KMeansTrainer(BaseModelTrainer):
    """K-均值聚类训练器
    
    训练K-Means聚类模型，用于无监督学习的聚类分析。
    对应前端组件ID: kmeans
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        训练K-Means聚类模型
        
        Args:
            inputs: 输入数据，包括:
                - train: 训练数据集
                - test: 测试数据集（可选）
            parameters: 参数，包括:
                - features: 特征列
                - n_clusters: 聚类数量
                - init: 初始化方法（k-means++、random）
                - max_iter: 最大迭代次数
                - random_state: 随机种子
                
        Returns:
            ExecutionResult: 执行结果，包含训练好的模型和聚类结果
        """
        try:
            # 获取输入数据
            if 'train' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少训练数据集"
                )
            
            train_dataset = inputs.get('train', {})
            test_dataset = inputs.get('test', {})
            
            # 获取参数
            features = parameters.get('features', '')
            n_clusters = int(parameters.get('n_clusters', 3))
            init = parameters.get('init', 'k-means++')
            max_iter = int(parameters.get('max_iter', 300))
            random_state = int(parameters.get('random_state', 42))
            
            # 如果特征是字符串，分割为列表
            if isinstance(features, str) and features:
                features = [f.strip() for f in features.split(',') if f.strip()]
            
            # 准备数据处理代码（聚类不需要目标变量）
            data_prep_code = """
try:
    import pandas as pd
    import numpy as np
    import json
    
    # 解析训练数据集
    train_df = pd.read_json('''{json.dumps(train_dataset.get('data', '{}'))}''', orient='split')
    
    # 确定特征列
    if {repr(features)}:
        feature_cols = [col for col in {repr(features)} if col in train_df.columns]
    else:
        # 使用所有数值列作为特征
        feature_cols = [col for col in train_df.columns if pd.api.types.is_numeric_dtype(train_df[col])]
    
    if not feature_cols:
        raise ValueError("没有有效的特征列")
    
    # 准备特征矩阵
    X_train = train_df[feature_cols].values
    
    # 检查数据有效性
    if np.isnan(X_train).any():
        raise ValueError("数据集包含NaN值，请先进行数据清洗")
""".format(
                json.dumps(train_dataset.get('data', '{}')),
                repr(features)
            )
            
            # 准备测试数据代码
            test_data_code = """
# 处理测试数据集
X_test = None
test_df = None
if {test_exists}:
    try:
        test_df = pd.read_json('''{test_data}''', orient='split')
        # 使用与训练集相同的特征
        if feature_cols and all(col in test_df.columns for col in feature_cols):
            X_test = test_df[feature_cols].values
    except Exception as e:
        print(f"警告: 测试数据集处理失败: {{str(e)}}")
""".format(
                test_exists=bool(test_dataset),
                test_data=json.dumps(test_dataset.get('data', '{}'))
            )
            
            # 模型训练代码
            model_code = f"""
# 导入必要的库
from sklearn.cluster import KMeans
import pickle
import base64
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score

# 创建并训练K-Means模型
model = KMeans(
    n_clusters={n_clusters},
    init='{init}',
    max_iter={max_iter},
    random_state={random_state}
)

# 训练模型
model.fit(X_train)

# 获取模型属性
cluster_centers = model.cluster_centers_.tolist()
labels = model.labels_.tolist()
inertia = float(model.inertia_)

# 获取聚类质量评估指标
try:
    if len(np.unique(labels)) > 1 and len(X_train) > len(np.unique(labels)):
        silhouette = float(silhouette_score(X_train, labels))
        calinski = float(calinski_harabasz_score(X_train, labels))
        davies = float(davies_bouldin_score(X_train, labels))
    else:
        silhouette = 0
        calinski = 0
        davies = 0
except Exception as e:
    silhouette = 0
    calinski = 0
    davies = 0
    print(f"警告: 聚类评估指标计算失败: {{str(e)}}")

# 保存模型
model_bytes = pickle.dumps(model)
model_data = base64.b16encode(model_bytes).decode('utf-8')

# 聚类结果数据框
train_df['cluster'] = labels
cluster_stats = []

# 计算每个聚类的统计信息
for i in range({n_clusters}):
    cluster_df = train_df[train_df['cluster'] == i]
    if not cluster_df.empty:
        # 计算每个特征的均值和标准差
        stats = {{
            'cluster_id': i,
            'size': len(cluster_df),
            'percentage': float(len(cluster_df) / len(train_df) * 100),
            'feature_stats': {{}}
        }}
        
        for feat in feature_cols:
            if pd.api.types.is_numeric_dtype(cluster_df[feat]):
                stats['feature_stats'][feat] = {{
                    'mean': float(cluster_df[feat].mean()),
                    'std': float(cluster_df[feat].std()),
                    'min': float(cluster_df[feat].min()),
                    'max': float(cluster_df[feat].max())
                }}
        
        cluster_stats.append(stats)

# 模型信息
model_info = {{
    'type': 'kmeans',
    'n_clusters': {n_clusters},
    'init': '{init}',
    'max_iter': {max_iter},
    'centers': cluster_centers,
    'feature_names': feature_cols,
    'model_data': model_data
}}

# 评估指标
metrics = {{
    'inertia': inertia,
    'silhouette_score': silhouette,
    'calinski_harabasz_score': calinski,
    'davies_bouldin_score': davies
}}

# 聚类结果
train_results = {{
    'labels': labels,
    'cluster_stats': cluster_stats
}}
"""
            
            # 添加预测代码
            prediction_code = """
# 准备结果字典
result = {
    'model_info': model_info,
    'metrics': metrics,
    'train_results': train_results
}

# 添加测试集预测结果
if X_test is not None:
    test_labels = model.predict(X_test).tolist()
    
    # 如果测试数据框存在
    if test_df is not None:
        test_df['cluster'] = test_labels
        
        # 聚类分布
        test_distribution = {}
        for i in range({n_clusters}):
            test_distribution[str(i)] = int((np.array(test_labels) == i).sum())
        
        # 测试结果
        test_results = {
            'labels': test_labels,
            'distribution': test_distribution
        }
        
        result['test_results'] = test_results

# 计算特征重要性（基于聚类中心的方差）
# 对于KMeans，我们可以基于聚类中心的离散程度来估计特征重要性
feature_importance = {}
centers_array = np.array(cluster_centers)
if centers_array.shape[0] > 1:  # 至少有两个聚类
    # 计算每个特征在聚类中心上的方差
    feature_variances = np.var(centers_array, axis=0)
    total_variance = np.sum(feature_variances)
    
    if total_variance > 0:
        # 将方差归一化为重要性得分
        for i, feat in enumerate(feature_cols):
            if i < len(feature_variances):
                importance = feature_variances[i] / total_variance
                feature_importance[feat] = float(importance)
    else:
        # 如果方差为0，则均匀分配重要性
        for feat in feature_cols:
            feature_importance[feat] = 1.0 / len(feature_cols)
else:
    # 如果只有一个聚类，则均匀分配重要性
    for feat in feature_cols:
        feature_importance[feat] = 1.0 / len(feature_cols)

result['feature_importance'] = feature_importance

print(json.dumps(result))
"""
            
            # 将参数替换到预测代码中
            prediction_code = prediction_code.format(
                n_clusters=n_clusters
            )
            
            # 组合所有代码
            code = f"""
{data_prep_code}
{test_data_code}
{model_code}
{prediction_code}
"""
            
            # 在容器中执行
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"K-Means聚类模型训练失败: {output}"
                )
                
            # 解析输出
            try:
                result = json.loads(output)
                
                return ExecutionResult(
                    success=True,
                    output={
                        'model': result.get('model_info', {}),
                        'metrics': result.get('metrics', {}),
                        'train_results': result.get('train_results', {}),
                        'test_results': result.get('test_results', {}),
                        'feature_importance': result.get('feature_importance', {})
                    }
                )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error_message=f"解析K-Means聚类模型结果失败: {str(e)}\n输出: {output}"
                )
            
        except Exception as e:
            error_message = f"执行K-Means聚类训练器出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )
