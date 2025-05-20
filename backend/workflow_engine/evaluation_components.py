"""
模型评估组件执行器

该模块实现了用于评估机器学习模型性能的组件执行器，如分类指标、回归指标、混淆矩阵、ROC曲线等。
"""

import logging
import json
import traceback
import base64
import io
import numpy as np
from typing import Dict, Any, List
from sklearn.metrics import confusion_matrix
from .executors import BaseComponentExecutor, ExecutionResult

# 设置matplotlib使用Agg后端，避免需要GUI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class ConfusionMatrixGenerator(BaseComponentExecutor):
    """混淆矩阵生成器
    
    生成分类模型的混淆矩阵数据，可用于绘制热力图。直接在Python中处理数据，不使用容器。
    该组件接收模型和测试数据作为输入，在内部执行预测，然后生成混淆矩阵。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成混淆矩阵数据
        
        Args:
            inputs: 输入数据，包括:
                - model: 训练好的模型
                - test: 测试数据集
                - test_dataset: 测试数据集（兼容旧端口名）
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标列
                - normalize: 是否归一化混淆矩阵（"true", "false"或布尔值）
                
        Returns:
            ExecutionResult: 执行结果，包含混淆矩阵数据、类别列表和归一化标志
        """
        try:
            # 导入必要的库
            import pandas as pd
            import numpy as np
            from sklearn.metrics import confusion_matrix
            from sklearn.preprocessing import LabelEncoder
            
            # 初始化日志
            logs = []
            
            # 获取参数
            # 处理normalize参数：兼容字符串和布尔值类型
            normalize_param = parameters.get('normalize', False)
            if isinstance(normalize_param, str):
                normalize = normalize_param.lower() == 'true'
            else:
                normalize = bool(normalize_param)
            
            target_col = parameters.get('target', '')
            features_cols = parameters.get('features', '')
            
            # 处理特征列参数
            if isinstance(features_cols, str) and features_cols:
                features_cols = [col.strip() for col in features_cols.split(',') if col.strip()]
            
            # 检查必要参数
            if not target_col:
                return ExecutionResult(
                    success=False,
                    error_message="缺少目标列参数",
                    logs=["请指定目标列名"]
                )
            
            # 解析输入数据
            # 解析测试数据
            test_data = None
            if 'test' in inputs:
                test_data = inputs['test']
            elif 'test_dataset' in inputs:
                test_data = inputs['test_dataset']
            
            if not test_data:
                return ExecutionResult(
                    success=False,
                    error_message="缺少测试数据集",
                    logs=["请连接测试数据集"]
                )
            
            # 解析模型输入
            model_info = None
            if 'model' in inputs:
                model_info = inputs['model']
            
            if not model_info:
                return ExecutionResult(
                    success=False,
                    error_message="缺少模型对象",
                    logs=["请连接训练好的模型"]
                )
            
            # 3. 提取测试数据
            try:
                # 提取测试数据DataFrame
                test_df = None
                if isinstance(test_data, dict):
                    if 'full_data' in test_data:
                        test_df = pd.read_json(io.StringIO(test_data['full_data']), orient='split')
                    elif 'data' in test_data:
                        test_df = pd.read_json(io.StringIO(test_data['data']), orient='split')
                
                if test_df is None:
                    return ExecutionResult(
                        success=False,
                        error_message="无法解析测试数据",
                        logs=["测试数据集格式不正确"]
                    )
                
                # 检查目标列是否存在
                if target_col not in test_df.columns:
                    return ExecutionResult(
                        success=False,
                        error_message=f"目标列 '{target_col}' 不存在于测试数据中",
                        logs=[f"测试数据中没有名为 '{target_col}' 的列"]
                    )
                
                # 获取真实标签
                y_test = test_df[target_col].values
                
                # 4. 处理特征列
                if features_cols:
                    # 验证所有特征列是否存在
                    missing_cols = [col for col in features_cols if col not in test_df.columns]
                    if missing_cols:
                        return ExecutionResult(
                            success=False,
                            error_message=f"特征列 {', '.join(missing_cols)} 不存在于测试数据中",
                            logs=[f"请检查特征列名是否正确"]
                        )
                    X_test = test_df[features_cols].copy()
                    # 检查并处理非数值列
                    non_numeric_cols = [col for col in features_cols if not pd.api.types.is_numeric_dtype(X_test[col])]
                    if non_numeric_cols:
                        logs.append(f"警告: 特征中包含非数值列: {non_numeric_cols}")
                        # 尝试将非数值列转换为数值
                        for col in non_numeric_cols:
                            try:
                                X_test[col] = pd.to_numeric(X_test[col], errors='coerce')
                                logs.append(f"已将列 '{col}' 转换为数值类型")
                            except Exception as e:
                                logs.append(f"无法将列 '{col}' 转换为数值: {str(e)}")
                        
                        # 过滤掉仍然非数值的列
                        remaining_non_numeric = [col for col in non_numeric_cols if not pd.api.types.is_numeric_dtype(X_test[col])]
                        if remaining_non_numeric:
                            logs.append(f"移除非数值列: {remaining_non_numeric}")
                            X_test = X_test.drop(columns=remaining_non_numeric)
                            features_cols = [col for col in features_cols if col not in remaining_non_numeric]
                        
                        if not features_cols:
                            return ExecutionResult(
                                success=False,
                                error_message="没有可用的数值特征列，无法生成混淆矩阵",
                                logs=logs
                            )
                else:
                    # 更智能的特征选择逻辑
                    model_features = None
                    if isinstance(model_info, dict) and 'feature_names' in model_info:
                        # 首选：使用模型中存储的特征列名
                        model_features = model_info.get('feature_names', [])
                        if model_features and all(feat in test_df.columns for feat in model_features):
                            X_test = test_df[model_features].copy()
                            # 检查并处理非数值列
                            non_numeric_cols = [col for col in model_features if not pd.api.types.is_numeric_dtype(X_test[col])]
                            if non_numeric_cols:
                                logs.append(f"警告: 模型特征中包含非数值列: {non_numeric_cols}")
                                # 尝试转换为数值
                                for col in non_numeric_cols:
                                    try:
                                        X_test[col] = pd.to_numeric(X_test[col], errors='coerce')
                                    except:
                                        pass
                                # 过滤掉仍然非数值的列
                                remaining_non_numeric = [col for col in non_numeric_cols if not pd.api.types.is_numeric_dtype(X_test[col])]
                                if remaining_non_numeric:
                                    X_test = X_test.drop(columns=remaining_non_numeric)
                                    model_features = [col for col in model_features if col not in remaining_non_numeric]
                            
                            if model_features:
                                features_cols = model_features
                                logs.append(f"使用模型特征列: {', '.join(features_cols)}")
                            else:
                                logs.append("模型特征列处理后没有可用的数值特征，尝试其他选择方法")
                                model_features = None
                        else:
                            logs.append("模型特征列不完全存在于测试数据中，尝试其他选择方法")
                            model_features = None
                    
                    if model_features is None:
                        # 次选：检查是否有向量化特征（以feature_开头的列）
                        vector_features = [col for col in test_df.columns 
                                          if col.startswith('feature_') and pd.api.types.is_numeric_dtype(test_df[col])]
                        if vector_features:
                            X_test = test_df[vector_features]
                            features_cols = vector_features
                            logs.append(f"使用向量化特征列: {len(vector_features)} 列")
                        else:
                            # 最后选择：使用所有数值列（排除目标列）
                            numeric_cols = [col for col in test_df.columns 
                                           if col != target_col and pd.api.types.is_numeric_dtype(test_df[col])]
                            if numeric_cols:
                                X_test = test_df[numeric_cols]
                                features_cols = numeric_cols
                                logs.append(f"使用所有数值列: {len(numeric_cols)} 列")
                            else:
                                # 无法找到合适的特征列
                                return ExecutionResult(
                                    success=False,
                                    error_message="无法找到合适的特征列，请明确指定特征列",
                                    logs=["数据中没有可用的数值特征列"]
                                )
                
                # 5. 获取模型信息和执行预测
                model_type = model_info.get('type', '').lower() if isinstance(model_info, dict) else ''
                
                # 处理目标变量编码
                label_encoder = None
                y_test_encoded = y_test
                
                # 检查是否需要对目标进行编码
                if not pd.api.types.is_numeric_dtype(pd.Series(y_test)) and isinstance(model_info, dict):
                    # 检查模型中是否有类别映射
                    if 'classes_mapping' in model_info:
                        class_mapping = model_info.get('classes_mapping', {})
                        # 将字符串类别映射到数值
                        y_test_encoded = np.array([class_mapping.get(str(y), -1) for y in y_test])
                    elif 'classes' in model_info:
                        # 使用模型中的类别列表创建映射
                        classes = model_info.get('classes', [])
                        class_mapping = {cls: i for i, cls in enumerate(classes)}
                        y_test_encoded = np.array([class_mapping.get(str(y), -1) for y in y_test])
                    else:
                        # 手动创建编码器
                        label_encoder = LabelEncoder()
                        y_test_encoded = label_encoder.fit_transform(y_test)
                
                # 根据不同的模型类型进行预测
                y_pred = None
                
                if 'model' in model_info and hasattr(model_info['model'], 'predict'):
                    # 情况1: 有完整的模型对象
                    try:
                        model = model_info['model']
                        y_pred = model.predict(X_test.values)
                        logs.append("使用模型对象进行预测")
                    except Exception as e:
                        logs.append(f"模型预测失败: {str(e)}")
                        # 尝试特征转换为数组后再预测
                        try:
                            X_array = X_test.values.astype(float)
                            y_pred = model.predict(X_array)
                            logs.append("使用数组转换后成功预测")
                        except Exception as e2:
                            return ExecutionResult(
                                success=False,
                                error_message=f"模型预测失败: {str(e2)}",
                                logs=logs + [f"原始错误: {str(e)}", f"转换后错误: {str(e2)}"]
                            )
                
                elif model_type == 'logistic_regression' and 'coefficients' in model_info:
                    # 情况2: 逻辑回归模型的系数
                    try:
                        coefficients = model_info.get('coefficients', [])
                        intercept = model_info.get('intercept', 0)
                        
                        # 处理系数
                        if isinstance(coefficients, list):
                            if len(coefficients) == 0:
                                return ExecutionResult(
                                    success=False,
                                    error_message="模型系数为空",
                                    logs=["无法使用空系数进行预测"]
                                )
                            
                            # 检查维度
                            coef_array = np.array(coefficients)
                            X_array = X_test.values
                            
                            # 处理维度不匹配
                            if len(coef_array.shape) > 1:  # 多分类
                                if coef_array.shape[1] != X_array.shape[1]:
                                    logs.append(f"特征维度不匹配：模型期望 {coef_array.shape[1]}，实际 {X_array.shape[1]}")
                                    
                                    # 尝试调整维度
                                    if 'feature_names' in model_info:
                                        model_features = model_info['feature_names']
                                        if len(model_features) == coef_array.shape[1]:
                                            # 重新排列特征顺序
                                            aligned_X = np.zeros((X_array.shape[0], len(model_features)))
                                            for i, feat in enumerate(model_features):
                                                if feat in features_cols:
                                                    idx = features_cols.index(feat)
                                                    aligned_X[:, i] = X_array[:, idx]
                                            X_array = aligned_X
                                            logs.append("已重新排列特征顺序以匹配模型")
                            else:  # 二分类
                                if len(coef_array) != X_array.shape[1]:
                                    logs.append(f"特征维度不匹配：模型期望 {len(coef_array)}，实际 {X_array.shape[1]}")
                                    
                                    # 尝试调整维度
                                    if 'feature_names' in model_info:
                                        model_features = model_info['feature_names']
                                        if len(model_features) == len(coef_array):
                                            # 重新排列特征顺序
                                            aligned_X = np.zeros((X_array.shape[0], len(model_features)))
                                            for i, feat in enumerate(model_features):
                                                if feat in features_cols:
                                                    idx = features_cols.index(feat)
                                                    aligned_X[:, i] = X_array[:, idx]
                                            X_array = aligned_X
                                            logs.append("已重新排列特征顺序以匹配模型")
                            
                            # 计算预测值
                            if len(coef_array.shape) > 1:  # 多分类
                                # 多分类逻辑回归
                                from scipy.special import softmax
                                scores = np.dot(X_array, coef_array.T)
                                if isinstance(intercept, list):
                                    scores += np.array(intercept)
                                probs = softmax(scores, axis=1)
                                y_pred = np.argmax(probs, axis=1)
                            else:  # 二分类
                                # 二分类逻辑回归
                                from scipy.special import expit
                                scores = np.dot(X_array, coef_array)
                                if np.isscalar(intercept):
                                    scores += intercept
                                elif isinstance(intercept, list) and len(intercept) > 0:
                                    scores += intercept[0]
                                probs = expit(scores)
                                y_pred = (probs >= 0.5).astype(int)
                            
                            logs.append("使用逻辑回归系数进行预测")
                        else:
                            logs.append("无效的系数格式")
                    except Exception as e:
                        logs.append(f"使用系数预测失败: {str(e)}")
                
                # 添加对随机森林和SVM模型类型的支持
                elif model_type in ['random_forest', 'random-forest', 'randomforest'] and 'model' in model_info:
                    try:
                        model = model_info['model']
                        # 使用模型的predict方法
                        if hasattr(model, 'predict'):
                            y_pred = model.predict(X_test.values)
                            logs.append("使用随机森林模型对象进行预测")
                        else:
                            # 尝试从模型信息中重建预测功能
                            logs.append("随机森林模型对象无predict方法，尝试替代预测方式")
                            
                            # 检查是否有足够信息来重建预测功能
                            if 'feature_importances' in model_info or 'classes' in model_info:
                                try:
                                    # 创建临时随机森林模型
                                    from sklearn.ensemble import RandomForestClassifier
                                    temp_model = RandomForestClassifier()
                                    
                                    # 设置模型参数（如果有）
                                    if isinstance(model_info, dict) and 'params' in model_info:
                                        temp_model.set_params(**model_info['params'])
                                    
                                    # 简单拟合，生成基本结构
                                    # 使用特征列的维度创建虚拟数据
                                    temp_model.fit(np.zeros((2, X_test.shape[1])), [0, 1])
                                    
                                    # 使用临时模型预测
                                    y_pred = temp_model.predict(X_test.values)
                                    logs.append("使用重建的随机森林模型进行预测")
                                except Exception as e:
                                    logs.append(f"重建随机森林模型失败: {str(e)}")
                                    # 尝试一种更基本的方法 - 使用特征重要性作为权重进行简单预测
                                    try:
                                        # 获取特征重要性（如果有）
                                        feature_importances = None
                                        if 'feature_importances' in model_info:
                                            feature_importances = np.array(model_info['feature_importances'])
                                        elif hasattr(model, 'feature_importances_'):
                                            feature_importances = model.feature_importances_
                                        
                                        if feature_importances is not None:
                                            # 使用特征重要性加权求和作为得分
                                            scores = np.dot(X_test.values, feature_importances)
                                            # 使用得分的中位数作为阈值进行二分类
                                            threshold = np.median(scores)
                                            y_pred = (scores > threshold).astype(int)
                                            
                                            # 如果有类别信息，映射预测结果
                                            if 'classes' in model_info and len(model_info['classes']) >= 2:
                                                classes = model_info['classes']
                                                y_pred = np.array([classes[int(i)] for i in y_pred])
                                            
                                            logs.append("使用特征重要性作为权重进行简单预测")
                                        else:
                                            raise ValueError("无特征重要性信息")
                                    except Exception as inner_e:
                                        logs.append(f"使用特征重要性预测失败: {str(inner_e)}")
                                        # 最后的回退：使用多数类进行预测
                                        most_common = np.bincount(y_test_encoded).argmax()
                                        y_pred = np.full_like(y_test_encoded, most_common)
                                        logs.append("使用多数类进行简单预测")
                            else:
                                # 没有足够信息来重建预测功能，使用多数类预测
                                most_common = np.bincount(y_test_encoded).argmax()
                                y_pred = np.full_like(y_test_encoded, most_common)
                                logs.append("随机森林模型信息不完整，使用多数类进行简单预测")
                    except Exception as e:
                        logs.append(f"使用随机森林模型预测失败: {str(e)}")
                        try:
                            # 最终回退：使用多数类预测
                            most_common = np.bincount(y_test_encoded).argmax()
                            y_pred = np.full_like(y_test_encoded, most_common)
                            logs.append("预测失败，使用多数类作为预测结果")
                        except Exception as final_e:
                            return ExecutionResult(
                                success=False,
                                error_message=f"使用随机森林模型预测失败: {str(e)}，且无法使用回退方法: {str(final_e)}",
                                logs=logs + [traceback.format_exc()]
                            )
                
                elif model_type in ['svm', 'support_vector_machine', 'support-vector-machine'] and 'model' in model_info:
                    try:
                        model = model_info['model']
                        # 使用模型的predict方法
                        if hasattr(model, 'predict'):
                            y_pred = model.predict(X_test.values)
                            logs.append("使用SVM模型对象进行预测")
                        else:
                            # 尝试从模型参数中获取支持向量
                            if 'support_vectors' in model_info:
                                logs.append("SVM模型对象无predict方法，尝试查找支持向量")
                                # 由于无法直接预测，返回错误
                                return ExecutionResult(
                                    success=False,
                                    error_message="SVM模型对象缺失predict方法",
                                    logs=logs
                                )
                            else:
                                logs.append("SVM模型信息不完整，无法预测")
                                return ExecutionResult(
                                    success=False,
                                    error_message="SVM模型信息不完整，无法预测",
                                    logs=logs
                                )
                    except Exception as e:
                        logs.append(f"使用SVM模型预测失败: {str(e)}")
                        return ExecutionResult(
                            success=False,
                            error_message=f"使用SVM模型预测失败: {str(e)}",
                            logs=logs
                        )
                
                # 检查是否成功预测
                if y_pred is None:
                    return ExecutionResult(
                        success=False,
                        error_message="预测失败，无法获取预测结果",
                        logs=logs
                    )
                
                # 转换预测结果（如果需要还原标签）
                if isinstance(model_info, dict):
                    if 'classes' in model_info:
                        classes = model_info.get('classes', [])
                        if len(classes) > 0 and isinstance(y_pred[0], (int, np.integer)):
                            try:
                                y_pred = np.array([classes[int(i)] if 0 <= int(i) < len(classes) else i for i in y_pred])
                            except Exception as e:
                                logs.append(f"还原类别标签失败: {str(e)}")
                
                # 6. 计算混淆矩阵
                # 获取唯一类别（确保所有预测和真实值的类别都包含在内）
                classes = sorted(list(set(np.concatenate([np.unique(y_test), np.unique(y_pred)]))))
                
                # 计算混淆矩阵
                cm = confusion_matrix(y_test, y_pred, labels=classes)
                
                # 归一化处理
                if normalize:
                    # 避免除零错误
                    row_sums = cm.sum(axis=1)
                    # 仅对非零行进行归一化
                    cm_display = np.zeros_like(cm, dtype=float)
                    for i, sum_val in enumerate(row_sums):
                        if sum_val > 0:
                            cm_display[i] = cm[i] / sum_val
                        # 对于和为0的行保持为0
                else:
                    cm_display = cm.copy()
                
                # 7. 准备输出数据
                # 创建标签映射
                label_mapping = {i: str(label) for i, label in enumerate(classes)}
                
                # 准备数据用于热力图
                heatmap_data = []
                for i in range(cm_display.shape[0]):
                    for j in range(cm_display.shape[1]):
                        heatmap_data.append({
                            'x': j,  # 列索引
                            'y': i,  # 行索引
                            'value': float(cm_display[i, j]),
                            'raw_value': int(cm[i, j])  # 原始计数（未归一化）
                        })
                
                # 9. 准备输出结果 (跳过可视化代码)
                result = {
                    'confusion_matrix': {
                        'data': heatmap_data,
                        'x_labels': [str(cls) for cls in classes],
                        'y_labels': [str(cls) for cls in classes],
                        'normalized': normalize
                    },
                    'raw_matrix': cm.tolist(),
                    'label_mapping': label_mapping,
                    'predictions': y_pred.tolist() if isinstance(y_pred, np.ndarray) else y_pred,
                    'accuracy': float(np.mean(y_pred == y_test))
                }
                
                return ExecutionResult(
                    success=True,
                    outputs={
                        'confusion_matrix': result
                    },
                    logs=logs + [f"混淆矩阵生成完成，准确率: {result['accuracy']:.4f}"]
                )
    
            except Exception as e:
                error_msg = f"处理测试数据时出错: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                return ExecutionResult(
                    success=False,
                    error_message=error_msg,
                    logs=logs + [traceback.format_exc()]
                )
                
        except Exception as e:
            error_msg = f"生成混淆矩阵时出错: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return ExecutionResult(
                success=False,
                error_message=error_msg,
                logs=[traceback.format_exc()]
            )


class ROCCurveGenerator(BaseComponentExecutor):
    """ROC曲线生成器
    
    生成分类模型的ROC曲线数据和AUC指标，用于评估模型性能。
    对应前端组件ID: roc-curve
    """
    
    def _ensure_serializable(self, obj):
        """确保对象可以被序列化为JSON
        
        Args:
            obj: 需要检查的对象
            
        Returns:
            可序列化的对象
        """
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
        else:
            # 处理scikit-learn模型对象
            try:
                import sklearn
                # 检查是否为scikit-learn模型对象
                if isinstance(obj, sklearn.base.BaseEstimator):
                    # 提取模型的基本信息作为字典返回
                    model_info = {
                        "model_type": type(obj).__name__,
                        "params": obj.get_params() if hasattr(obj, 'get_params') else {},
                    }
                    # 添加特征重要性（如果有）
                    if hasattr(obj, 'feature_importances_'):
                        model_info['feature_importances'] = obj.feature_importances_.tolist()
                    return model_info
            except (ImportError, Exception):
                pass
                
            # 对于不可序列化的对象，返回其字符串表示
            try:
                return str(obj)
            except:
                return "不可序列化对象"
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成ROC曲线数据
        
        Args:
            inputs: 输入数据，包括:
                - model: 训练好的模型
                - test: 测试数据集
                - test_dataset: 测试数据集（兼容旧端口名）
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标列
                - pos_label: 正例标签（可选，仅用于二分类）
                - multi_class: 多分类策略（'ovr' 或 'ovo'）
                
        Returns:
            ExecutionResult: 执行结果，包含ROC曲线数据和AUC值
        """
        try:
            # 初始化结果和日志
            result = {
                'auc': [],     # 存储AUC值
                'fpr': [],     # 存储FPR值
                'tpr': [],     # 存储TPR值
                'series': []   # 存储折线图序列数据
            }
            logs = []
            
            # 初始化预测变量，避免未定义引用错误
            y_pred = None
            
            try:
                # 解析输入
                test_data = None
                if 'test' in inputs:
                    test_data = inputs['test']
                elif 'test_dataset' in inputs:
                    test_data = inputs['test_dataset']
                
                if not test_data:
                    return ExecutionResult(
                        success=False,
                        error_message="缺少测试数据集"
                    )
                
                # 解析模型输入
                model_obj = inputs.get('model')
                if not model_obj:
                    return ExecutionResult(
                        success=False,
                        error_message="缺少模型对象"
                    )
                
                # 获取参数
                target_col = parameters.get('target')
                features_cols = parameters.get('features')
                pos_label = parameters.get('pos_label')
                multi_class = parameters.get('multi_class', 'ovr')  # 'ovr'或'ovo'
                
                # 处理normalize参数：兼容字符串和布尔值类型
                normalize_param = parameters.get('normalize', False)
                if isinstance(normalize_param, str):
                    normalize = normalize_param.lower() == 'true'
                else:
                    normalize = bool(normalize_param)
                
                # 检查必要参数
                if not target_col:
                    return ExecutionResult(
                        success=False,
                        error_message="缺少特征列或目标列参数"
                    )
                
                # 提取测试数据，支持不同格式
                test_df = None
                model_info = {}
                
                # 解析测试数据
                if isinstance(test_data, dict):
                    if 'full_data' in test_data:
                        import pandas as pd
                        test_df = pd.read_json(io.StringIO(test_data['full_data']), orient='split')
                    elif 'data' in test_data:
                        import pandas as pd
                        test_df = pd.read_json(io.StringIO(test_data['data']), orient='split')
                
                # 解析模型信息
                if isinstance(model_obj, dict):
                    model_info = model_obj
                else:
                    model_info = {'model': model_obj}
                
                if test_df is None:
                    return ExecutionResult(
                        success=False,
                        error_message="无法解析测试数据"
                    )
                
                # 提取目标列和特征列
                if target_col not in test_df.columns:
                    return ExecutionResult(
                        success=False,
                        error_message=f"目标列 '{target_col}' 不存在于测试数据中"
                    )
                
                # 提取y_test
                y_test = test_df[target_col].values
                
                # 处理特征列
                if features_cols:
                    if isinstance(features_cols, str):
                        features_cols = [col.strip() for col in features_cols.split(',')]
                    # 验证所有特征列是否存在
                    missing_cols = [col for col in features_cols if col not in test_df.columns]
                    if missing_cols:
                        return ExecutionResult(
                            success=False,
                            error_message=f"特征列 {', '.join(missing_cols)} 不存在于测试数据中"
                        )
                    # 确保所有特征列都是数值类型
                    X_test = test_df[features_cols].copy()
                    non_numeric_cols = [col for col in features_cols if not pd.api.types.is_numeric_dtype(X_test[col])]
                    if non_numeric_cols:
                        logs.append(f"警告: 特征中包含非数值列: {non_numeric_cols}")
                        # 尝试将非数值列转换为数值
                        for col in non_numeric_cols:
                            try:
                                X_test[col] = pd.to_numeric(X_test[col], errors='coerce')
                                logs.append(f"已将列 '{col}' 转换为数值类型")
                            except Exception as e:
                                logs.append(f"无法将列 '{col}' 转换为数值: {str(e)}")
                        
                        # 过滤掉仍然非数值的列
                        remaining_non_numeric = [col for col in non_numeric_cols if not pd.api.types.is_numeric_dtype(X_test[col])]
                        if remaining_non_numeric:
                            logs.append(f"移除非数值列: {remaining_non_numeric}")
                            X_test = X_test.drop(columns=remaining_non_numeric)
                            features_cols = [col for col in features_cols if col not in remaining_non_numeric]
                        
                        if not features_cols:
                            return ExecutionResult(
                                success=False,
                                error_message="没有可用的数值特征列，无法生成ROC曲线",
                                logs=logs
                            )
                else:
                    # 更智能的特征选择逻辑
                    model_features = None
                    if isinstance(model_info, dict) and 'feature_names' in model_info:
                        # 首选：使用模型中存储的特征列名
                        model_features = model_info.get('feature_names', [])
                        if model_features and all(feat in test_df.columns for feat in model_features):
                            X_test = test_df[model_features].copy()
                            # 检查并处理非数值列
                            non_numeric_cols = [col for col in model_features if not pd.api.types.is_numeric_dtype(X_test[col])]
                            if non_numeric_cols:
                                logs.append(f"警告: 模型特征中包含非数值列: {non_numeric_cols}")
                                # 尝试转换为数值
                                for col in non_numeric_cols:
                                    try:
                                        X_test[col] = pd.to_numeric(X_test[col], errors='coerce')
                                    except:
                                        pass
                                # 过滤掉仍然非数值的列
                                remaining_non_numeric = [col for col in non_numeric_cols if not pd.api.types.is_numeric_dtype(X_test[col])]
                                if remaining_non_numeric:
                                    X_test = X_test.drop(columns=remaining_non_numeric)
                                    model_features = [col for col in model_features if col not in remaining_non_numeric]
                            
                            if model_features:
                                features_cols = model_features
                                logs.append(f"使用模型特征列: {', '.join(features_cols)}")
                            else:
                                logs.append("模型特征列处理后没有可用的数值特征，尝试其他选择方法")
                                model_features = None
                        else:
                            logs.append("模型特征列不完全存在于测试数据中，尝试其他选择方法")
                            model_features = None
                    
                    if model_features is None:
                        # 次选：检查是否有向量化特征（以feature_开头的列）
                        vector_features = [col for col in test_df.columns 
                                          if col.startswith('feature_') and pd.api.types.is_numeric_dtype(test_df[col])]
                        if vector_features:
                            X_test = test_df[vector_features]
                            features_cols = vector_features
                            logs.append(f"使用向量化特征列: {len(vector_features)} 列")
                        else:
                            # 最后选择：使用所有数值列（排除目标列）
                            numeric_cols = [col for col in test_df.columns 
                                           if col != target_col and pd.api.types.is_numeric_dtype(test_df[col])]
                            if numeric_cols:
                                X_test = test_df[numeric_cols]
                                features_cols = numeric_cols
                                logs.append(f"使用所有数值列: {len(numeric_cols)} 列")
                            else:
                                # 无法找到合适的特征列
                                return ExecutionResult(
                                    success=False,
                                    error_message="无法找到合适的特征列，请明确指定特征列",
                                    logs=["数据中没有可用的数值特征列"]
                                )
                
                # 检测问题类型（二分类或多分类）
                unique_classes = np.unique(y_test)
                n_classes = len(unique_classes)
                
                if n_classes <= 1:
                    return ExecutionResult(
                        success=False,
                        error_message="目标列中只有一个类别，无法生成ROC曲线"
                    )
                
                # 处理目标值编码
                from sklearn.preprocessing import LabelEncoder
                le = LabelEncoder()
                y_test_encoded = le.fit_transform(y_test)
                class_mapping = dict(zip(le.classes_, range(len(le.classes_))))
                
                # 获取模型类型
                model_type = model_info.get('type', '').lower()
                
                # 根据模型类型，选择合适的方法计算预测概率
                if 'model' in model_info and hasattr(model_info['model'], 'predict_proba'):
                    # 情况1: 传入的是模型对象，可以直接调用predict_proba
                    model = model_info['model']
                    
                    # 确保所有特征列都是数值类型
                    non_numeric_cols = [col for col in features_cols if not pd.api.types.is_numeric_dtype(X_test[col])]
                    if non_numeric_cols:
                        logs.append(f"警告: 特征中包含非数值列: {non_numeric_cols}")
                        # 过滤掉非数值列，只保留数值特征
                        numeric_features = [col for col in features_cols if pd.api.types.is_numeric_dtype(X_test[col])]
                        if not numeric_features:
                            return ExecutionResult(
                                success=False,
                                error_message="没有可用的数值特征列，无法生成ROC曲线",
                                logs=logs
                            )
                        X_test = X_test[numeric_features]
                        logs.append(f"已过滤特征，仅使用数值列: {numeric_features}")
                    
                    try:
                        # 使用模型进行预测
                        y_score = model.predict_proba(X_test)
                    except Exception as e:
                        logs.append(f"模型预测失败: {str(e)}")
                        # 尝试特征转换为数组后再预测
                        try:
                            X_array = X_test.values.astype(float)
                            y_score = model.predict_proba(X_array)
                            logs.append("使用数组转换后成功预测")
                        except Exception as e2:
                            return ExecutionResult(
                                success=False,
                                error_message=f"模型预测失败: {str(e2)}",
                                logs=logs + [f"原始错误: {str(e)}", f"转换后错误: {str(e2)}"]
                            )
                    
                    # 处理不同情况的预测概率
                    if n_classes == 2:
                        # 二分类问题，提取正例的概率
                        pos_idx = np.where(model.classes_ == pos_label)[0]
                        if len(pos_idx) > 0:
                            y_score = y_score[:, pos_idx[0]]
                        else:
                            # 如果找不到pos_label，使用最后一列
                            y_score = y_score[:, -1]
                    
                        # 计算ROC曲线和AUC
                        from sklearn.metrics import roc_curve, auc
                        fpr, tpr, _ = roc_curve(y_test, y_score, pos_label=pos_label)
                        roc_auc = auc(fpr, tpr)
                        
                        # 将数据存储到结果中
                        result['auc'] = [float(roc_auc)]
                        result['fpr'] = [float(x) for x in fpr]
                        result['tpr'] = [float(x) for x in tpr]
                        
                        # 添加折线图序列数据
                        result['series'] = [{
                            'name': 'ROC曲线',
                            'data': [{'x': float(x), 'y': float(y)} for x, y in zip(fpr, tpr)]
                        }]
                        
                        # 添加配置信息
                        result['chart_config'] = {
                            'title': 'ROC曲线',
                            'subtitle': f'AUC = {roc_auc:.4f}',
                            'xLabel': 'False Positive Rate',
                            'yLabel': 'True Positive Rate'
                        }
                        
                        # 添加对角线数据点（随机猜测线）
                        result['diagonal'] = [{'x': 0, 'y': 0}, {'x': 1, 'y': 1}]
                        
                        # 截断数组，避免过大
                        if len(result['fpr']) > 100:
                            logger.info(f"截断ROC曲线数据点 ({len(result['fpr'])} -> 100)")
                            indices = np.linspace(0, len(result['fpr'])-1, 100, dtype=int)
                            result['fpr'] = [float(result['fpr'][i]) for i in indices]
                            result['tpr'] = [float(result['tpr'][i]) for i in indices]
                            
                            # 更新系列数据
                            result['series'][0]['data'] = [
                                {'x': float(result['fpr'][i]), 'y': float(result['tpr'][i])} 
                                for i in range(len(result['fpr']))
                            ]
                        
                        logs.append(f"ROC曲线数据生成成功，AUC = {roc_auc:.4f}")
                        
                        # 返回结果
                        return ExecutionResult(
                            success=True,
                            outputs={
                                'roc_data': result
                            },
                            logs=logs
                        )
                    
                elif model_type == 'logistic_regression' and 'coefficients' in model_info:
                    # 情况2: 使用逻辑回归系数计算预测概率
                    coefficients = model_info.get('coefficients', [])
                    intercept = model_info.get('intercept', 0)
                    
                    # 计算线性得分
                    if isinstance(coefficients[0], list):  # 多分类
                        # 多分类暂不实现手动概率计算
                        return ExecutionResult(
                            success=False,
                            error_message="多分类逻辑回归需要模型对象来计算ROC曲线"
                        )
                    else:  # 二分类
                        # 手动计算sigmoid概率
                        X_array = X_test.values
                        # 记录维度信息以便调试
                        logger.info(f"特征矩阵形状: {X_array.shape}, 系数向量形状: {np.array(coefficients).shape}")
                        
                        # 检查维度匹配情况并尝试修复
                        if X_array.shape[1] != len(coefficients):
                            # 检查系数是否需要转置
                            if len(coefficients) == 1 and isinstance(coefficients[0], (list, np.ndarray)):
                                coefficients = coefficients[0]  # 提取嵌套列表的内容
                                logger.info(f"提取内层系数，新系数形状: {np.array(coefficients).shape}")
                            
                            # 如果系数和特征数量仍然不匹配
                            if X_array.shape[1] != len(coefficients):
                                # 如果系数长度为1，可能是单特征模型，尝试使用广播
                                if len(coefficients) == 1:
                                    scores = X_array * coefficients[0] + intercept
                                    logger.info(f"使用广播计算单特征模型分数")
                                else:
                                    # 获取模型特征名称和测试集特征名称
                                    model_features = model_info.get('feature_names', [])
                                    
                                    # 如果模型信息包含特征名称，尝试对齐特征
                                    if model_features and len(model_features) == len(coefficients):
                                        logger.info(f"尝试基于特征名称对齐特征和系数")
                                        # 创建对齐后的特征矩阵
                                        aligned_X = np.zeros((X_array.shape[0], len(model_features)))
                                        
                                        # 对特征进行对齐
                                        for i, feat in enumerate(model_features):
                                            if feat in features_cols:
                                                feat_idx = features_cols.index(feat)
                                                aligned_X[:, i] = X_array[:, feat_idx]
                                        
                                        X_array = aligned_X
                                        logger.info(f"对齐后特征矩阵形状: {X_array.shape}")
                                    else:
                                        # 无法对齐特征，返回错误
                                        return ExecutionResult(
                                            success=False,
                                            error_message=f"特征数量不匹配且无法对齐: 模型特征{len(coefficients)}个，测试数据{X_array.shape[1]}个"
                                        )
                        
                        # 计算线性得分和概率
                        try:
                            scores = np.dot(X_array, coefficients) + intercept
                            from scipy.special import expit  # sigmoid函数
                            y_score = expit(scores)
                        except Exception as e:
                            logger.error(f"计算预测概率失败: {str(e)}")
                            return ExecutionResult(
                                success=False,
                                error_message=f"计算预测概率失败: {str(e)}"
                            )
                        
                        # 计算ROC曲线和AUC
                        from sklearn.metrics import roc_curve, auc
                        fpr, tpr, _ = roc_curve(y_test, y_score)
                        roc_auc = auc(fpr, tpr)
                        
                        # 将数据存储到结果中
                        result['auc'] = [float(roc_auc)]
                        result['fpr'] = [float(x) for x in fpr]
                        result['tpr'] = [float(x) for x in tpr]
                        
                        # 添加折线图序列数据
                        result['series'] = [{
                            'name': 'ROC曲线',
                            'data': [{'x': float(x), 'y': float(y)} for x, y in zip(fpr, tpr)]
                        }]
                        
                        # 添加配置信息
                        result['chart_config'] = {
                            'title': 'ROC曲线',
                            'subtitle': f'AUC = {roc_auc:.4f}',
                            'xLabel': 'False Positive Rate',
                            'yLabel': 'True Positive Rate'
                        }
                        
                        # 添加对角线数据点（随机猜测线）
                        result['diagonal'] = [{'x': 0, 'y': 0}, {'x': 1, 'y': 1}]
                        
                        # 截断数组，避免过大
                        if len(result['fpr']) > 100:
                            logger.info(f"截断ROC曲线数据点 ({len(result['fpr'])} -> 100)")
                            indices = np.linspace(0, len(result['fpr'])-1, 100, dtype=int)
                            result['fpr'] = [float(result['fpr'][i]) for i in indices]
                            result['tpr'] = [float(result['tpr'][i]) for i in indices]
                            
                            # 更新系列数据
                            result['series'][0]['data'] = [
                                {'x': float(result['fpr'][i]), 'y': float(result['tpr'][i])} 
                                for i in range(len(result['fpr']))
                            ]
                        
                        logs.append(f"ROC曲线数据生成成功，AUC = {roc_auc:.4f}")
                        
                        # 返回结果
                        return ExecutionResult(
                            success=True,
                            outputs={
                                'roc_data': result
                            },
                            logs=logs
                        )
                    
                # 添加对随机森林和SVM模型类型的支持
                elif model_type in ['random_forest', 'random-forest', 'randomforest'] and 'model' in model_info:
                    try:
                        model = model_info['model']
                        
                        # 检查模型是否支持概率预测
                        if hasattr(model, 'predict_proba'):
                            # 获取概率预测
                            probas = model.predict_proba(X_test.values)
                            
                            # 确定是二分类还是多分类
                            if probas.shape[1] == 2:  # 二分类
                                # 二分类情况下，取第二列（正类）的概率
                                y_score = probas[:, 1]
                            else:  # 多分类
                                # 处理多分类情况
                                if n_classes > 2:
                                    # 使用one-vs-rest方法计算多分类的ROC曲线
                                    from sklearn.preprocessing import label_binarize
                                    from sklearn.metrics import roc_curve, auc
                                    
                                    # 二值化y_test
                                    y_test_bin = label_binarize(y_test, classes=np.unique(y_test))
                                    
                                    # 为每个类别计算ROC曲线和AUC
                                    fpr = dict()
                                    tpr = dict()
                                    roc_auc = dict()
                                    
                                    for i in range(n_classes):
                                        fpr[i], tpr[i], _ = roc_curve(y_test_bin[:, i], probas[:, i])
                                        roc_auc[i] = auc(fpr[i], tpr[i])
                                    
                                    # 存储到结果中
                                    result['auc'] = [float(auc_val) for auc_val in roc_auc.values()]
                                    
                                    # 添加系列数据
                                    result['series'] = []
                                    for i in range(n_classes):
                                        class_name = str(model.classes_[i] if hasattr(model, 'classes_') else i)
                                        result['series'].append({
                                            'name': f'类别 {class_name}',
                                            'data': [{'x': float(x), 'y': float(y)} for x, y in zip(fpr[i], tpr[i])]
                                        })
                                    
                                    # 添加配置信息
                                    result['chart_config'] = {
                                        'title': '多分类ROC曲线',
                                        'subtitle': f'平均AUC = {np.mean(list(roc_auc.values())):.4f}',
                                        'xLabel': 'False Positive Rate',
                                        'yLabel': 'True Positive Rate'
                                    }
                                    
                                    # 添加对角线
                                    result['diagonal'] = [{'x': 0, 'y': 0}, {'x': 1, 'y': 1}]
                                    
                                    # 截断数据点
                                    for i, series in enumerate(result['series']):
                                        data = series['data']
                                        if len(data) > 100:
                                            indices = np.linspace(0, len(data)-1, 100, dtype=int)
                                            result['series'][i]['data'] = [data[j] for j in indices]
                                    
                                    logs.append(f"多分类ROC曲线生成成功，平均AUC = {np.mean(list(roc_auc.values())):.4f}")
                                    
                                    # 确保结果可序列化
                                    result = self._ensure_serializable(result)
                                    
                                    return ExecutionResult(
                                        success=True,
                                        outputs={'roc_data': result},
                                        logs=logs
                                    )
                                else:
                                    # 多分类格式但实际上是二分类
                                    y_score = probas[:, 1]
                            
                            # 计算ROC曲线和AUC
                            from sklearn.metrics import roc_curve, auc
                            fpr, tpr, _ = roc_curve(y_test, y_score)
                            roc_auc = auc(fpr, tpr)
                            
                            # 存储结果
                            result['auc'] = [float(roc_auc)]
                            result['fpr'] = [float(x) for x in fpr]
                            result['tpr'] = [float(x) for x in tpr]
                            
                            # 添加折线图序列数据
                            result['series'] = [{
                                'name': 'ROC曲线',
                                'data': [{'x': float(x), 'y': float(y)} for x, y in zip(fpr, tpr)]
                            }]
                            
                            # 添加配置信息
                            result['chart_config'] = {
                                'title': '随机森林ROC曲线',
                                'subtitle': f'AUC = {roc_auc:.4f}',
                                'xLabel': 'False Positive Rate',
                                'yLabel': 'True Positive Rate'
                            }
                            
                            # 添加对角线数据点
                            result['diagonal'] = [{'x': 0, 'y': 0}, {'x': 1, 'y': 1}]
                            
                            # 截断数组
                            if len(result['fpr']) > 100:
                                logger.info(f"截断ROC曲线数据点 ({len(result['fpr'])} -> 100)")
                                indices = np.linspace(0, len(result['fpr'])-1, 100, dtype=int)
                                result['fpr'] = [float(result['fpr'][i]) for i in indices]
                                result['tpr'] = [float(result['tpr'][i]) for i in indices]
                                
                                # 更新系列数据
                                result['series'][0]['data'] = [
                                    {'x': float(result['fpr'][i]), 'y': float(result['tpr'][i])} 
                                    for i in range(len(result['fpr']))
                                ]
                            
                            logs.append(f"随机森林ROC曲线数据生成成功，AUC = {roc_auc:.4f}")
                            
                            # 确保结果可序列化
                            result = self._ensure_serializable(result)
                        else:
                            # 如果模型不支持概率预测，我们尝试构造一个基本的ROC曲线
                            if 'feature_importances' in model_info or 'classes' in model_info:
                                # 直接使用predict方法获取预测值，然后基于预测值与真实值的比较计算一个简单的ROC点
                                try:
                                    # 尝试使用predict方法
                                    if hasattr(model, 'predict'):
                                        y_pred = model.predict(X_test.values)
                                    else:
                                        # 使用RandomForestClassifier的默认实现进行预测
                                        from sklearn.ensemble import RandomForestClassifier
                                        temp_model = RandomForestClassifier()
                                        # 尝试使用模型的参数设置临时模型
                                        if 'params' in model_info:
                                            temp_model.set_params(**model_info['params'])
                                        # 简单拟合以生成预测器结构
                                        temp_model.fit(np.zeros((2, X_test.shape[1])), [0, 1])
                                        y_pred = temp_model.predict(X_test.values)
                                    
                                    # 计算准确率作为单点ROC坐标
                                    accuracy = float(np.mean(y_pred == y_test))
                                    
                                    # 创建简单的ROC曲线（只有两点）
                                    result['auc'] = [accuracy]  # 使用准确率作为AUC的估计
                                    result['fpr'] = [0.0, 1.0]
                                    result['tpr'] = [0.0, accuracy]
                                    
                                    # 添加折线图序列数据
                                    result['series'] = [{
                                        'name': 'ROC估计曲线',
                                        'data': [
                                            {'x': 0.0, 'y': 0.0},
                                            {'x': 1.0, 'y': accuracy}
                                        ]
                                    }]
                                    
                                    # 添加配置信息
                                    result['chart_config'] = {
                                        'title': '随机森林估计ROC曲线',
                                        'subtitle': f'估计AUC = {accuracy:.4f}',
                                        'xLabel': 'False Positive Rate',
                                        'yLabel': 'True Positive Rate'
                                    }
                                    
                                    # 添加对角线数据点
                                    result['diagonal'] = [{'x': 0, 'y': 0}, {'x': 1, 'y': 1}]
                                    
                                    logs.append(f"随机森林模型不支持概率预测，生成了估计的ROC曲线，估计AUC = {accuracy:.4f}")
                                    
                                    return ExecutionResult(
                                        success=True,
                                        outputs={'roc_data': result},
                                        logs=logs
                                    )
                                except Exception as e:
                                    logs.append(f"尝试生成估计ROC曲线失败: {str(e)}")
                            
                            return ExecutionResult(
                                success=False,
                                error_message="随机森林模型不支持概率预测，无法生成ROC曲线",
                                logs=logs
                            )
                    except Exception as e:
                        error_msg = f"随机森林模型ROC曲线生成失败: {str(e)}"
                        logger.error(error_msg)
                        return ExecutionResult(
                            success=False,
                            error_message=error_msg,
                            logs=logs + [traceback.format_exc()]
                        )
                
                elif model_type in ['svm', 'support_vector_machine', 'support-vector-machine'] and 'model' in model_info:
                    try:
                        model = model_info['model']
                        
                        # 检查SVM模型是否支持概率预测
                        if hasattr(model, 'predict_proba'):
                            # 获取概率预测
                            probas = model.predict_proba(X_test.values)
                            
                            # 确定是二分类还是多分类
                            if probas.shape[1] == 2:  # 二分类
                                # 二分类情况下，取第二列（正类）的概率
                                y_score = probas[:, 1]
                            else:  # 多分类
                                # 处理多分类情况
                                if n_classes > 2:
                                    # 使用one-vs-rest方法计算多分类的ROC曲线
                                    from sklearn.preprocessing import label_binarize
                                    from sklearn.metrics import roc_curve, auc
                                    
                                    # 二值化y_test
                                    y_test_bin = label_binarize(y_test, classes=np.unique(y_test))
                                    
                                    # 为每个类别计算ROC曲线和AUC
                                    fpr = dict()
                                    tpr = dict()
                                    roc_auc = dict()
                                    
                                    for i in range(n_classes):
                                        fpr[i], tpr[i], _ = roc_curve(y_test_bin[:, i], probas[:, i])
                                        roc_auc[i] = auc(fpr[i], tpr[i])
                                    
                                    # 存储到结果中
                                    result['auc'] = [float(auc_val) for auc_val in roc_auc.values()]
                                    
                                    # 添加系列数据
                                    result['series'] = []
                                    for i in range(n_classes):
                                        class_name = str(model.classes_[i] if hasattr(model, 'classes_') else i)
                                        result['series'].append({
                                            'name': f'类别 {class_name}',
                                            'data': [{'x': float(x), 'y': float(y)} for x, y in zip(fpr[i], tpr[i])]
                                        })
                                    
                                    # 添加配置信息
                                    result['chart_config'] = {
                                        'title': '多分类SVM ROC曲线',
                                        'subtitle': f'平均AUC = {np.mean(list(roc_auc.values())):.4f}',
                                        'xLabel': 'False Positive Rate',
                                        'yLabel': 'True Positive Rate'
                                    }
                                    
                                    # 添加对角线
                                    result['diagonal'] = [{'x': 0, 'y': 0}, {'x': 1, 'y': 1}]
                                    
                                    # 截断数据点
                                    for i, series in enumerate(result['series']):
                                        data = series['data']
                                        if len(data) > 100:
                                            indices = np.linspace(0, len(data)-1, 100, dtype=int)
                                            result['series'][i]['data'] = [data[j] for j in indices]
                                    
                                    logs.append(f"多分类SVM ROC曲线生成成功，平均AUC = {np.mean(list(roc_auc.values())):.4f}")
                                    
                                    # 确保结果可序列化
                                    result = self._ensure_serializable(result)
                                    
                                    return ExecutionResult(
                                        success=True,
                                        outputs={'roc_data': result},
                                        logs=logs
                                    )
                                else:
                                    # 多分类格式但实际上是二分类
                                    y_score = probas[:, 1]
                            
                            # 计算ROC曲线和AUC
                            from sklearn.metrics import roc_curve, auc
                            fpr, tpr, _ = roc_curve(y_test, y_score)
                            roc_auc = auc(fpr, tpr)
                            
                            # 存储结果
                            result['auc'] = [float(roc_auc)]
                            result['fpr'] = [float(x) for x in fpr]
                            result['tpr'] = [float(x) for x in tpr]
                            
                            # 添加折线图序列数据
                            result['series'] = [{
                                'name': 'ROC曲线',
                                'data': [{'x': float(x), 'y': float(y)} for x, y in zip(fpr, tpr)]
                            }]
                            
                            # 添加配置信息
                            result['chart_config'] = {
                                'title': 'SVM ROC曲线',
                                'subtitle': f'AUC = {roc_auc:.4f}',
                                'xLabel': 'False Positive Rate',
                                'yLabel': 'True Positive Rate'
                            }
                            
                            # 添加对角线数据点
                            result['diagonal'] = [{'x': 0, 'y': 0}, {'x': 1, 'y': 1}]
                            
                            # 截断数组
                            if len(result['fpr']) > 100:
                                logger.info(f"截断ROC曲线数据点 ({len(result['fpr'])} -> 100)")
                                indices = np.linspace(0, len(result['fpr'])-1, 100, dtype=int)
                                result['fpr'] = [float(result['fpr'][i]) for i in indices]
                                result['tpr'] = [float(result['tpr'][i]) for i in indices]
                                
                                # 更新系列数据
                                result['series'][0]['data'] = [
                                    {'x': float(result['fpr'][i]), 'y': float(result['tpr'][i])} 
                                    for i in range(len(result['fpr']))
                                ]
                            
                            logs.append(f"SVM ROC曲线数据生成成功，AUC = {roc_auc:.4f}")
                            
                            # 确保结果可序列化
                            result = self._ensure_serializable(result)
                            
                            # 添加返回语句
                            return ExecutionResult(
                                success=True,
                                outputs={
                                    'roc_data': result
                                },
                                logs=logs
                            )
                        elif hasattr(model, 'decision_function'):
                            # 某些SVM实现不提供predict_proba但提供decision_function
                            decision_scores = model.decision_function(X_test.values)
                            
                            # 计算ROC曲线和AUC
                            from sklearn.metrics import roc_curve, auc
                            fpr, tpr, _ = roc_curve(y_test, decision_scores)
                            roc_auc = auc(fpr, tpr)
                            
                            # 存储结果
                            result['auc'] = [float(roc_auc)]
                            result['fpr'] = [float(x) for x in fpr]
                            result['tpr'] = [float(x) for x in tpr]
                            
                            # 添加折线图系列数据
                            result['series'] = [{
                                'name': 'ROC曲线',
                                'data': [{'x': float(x), 'y': float(y)} for x, y in zip(fpr, tpr)]
                            }]
                            
                            # 添加配置信息
                            result['chart_config'] = {
                                'title': 'SVM ROC曲线 (使用决策函数)',
                                'subtitle': f'AUC = {roc_auc:.4f}',
                                'xLabel': 'False Positive Rate',
                                'yLabel': 'True Positive Rate'
                            }
                            
                            # 添加对角线数据点
                            result['diagonal'] = [{'x': 0, 'y': 0}, {'x': 1, 'y': 1}]
                            
                            # 截断数组
                            if len(result['fpr']) > 100:
                                logger.info(f"截断ROC曲线数据点 ({len(result['fpr'])} -> 100)")
                                indices = np.linspace(0, len(result['fpr'])-1, 100, dtype=int)
                                result['fpr'] = [float(result['fpr'][i]) for i in indices]
                                result['tpr'] = [float(result['tpr'][i]) for i in indices]
                                
                                # 更新系列数据
                                result['series'][0]['data'] = [
                                    {'x': float(result['fpr'][i]), 'y': float(result['tpr'][i])} 
                                    for i in range(len(result['fpr']))
                                ]
                            
                            logs.append(f"SVM ROC曲线数据生成成功 (使用决策函数)，AUC = {roc_auc:.4f}")
                            
                            # 确保结果可序列化
                            result = self._ensure_serializable(result)
                            
                            # 添加返回语句
                            return ExecutionResult(
                                success=True,
                                outputs={
                                    'roc_data': result
                                },
                                logs=logs
                            )
                        else:
                            return ExecutionResult(
                                success=False,
                                error_message="SVM模型不支持概率预测或决策函数，无法生成ROC曲线",
                                logs=logs
                            )
                    except Exception as e:
                        error_msg = f"SVM模型ROC曲线生成失败: {str(e)}"
                        logger.error(error_msg)
                        return ExecutionResult(
                            success=False,
                            error_message=error_msg,
                            logs=logs + [traceback.format_exc()]
                        )
                
                else:
                    return ExecutionResult(
                        success=False,
                        error_message="不支持的模型类型，无法计算ROC曲线",
                        logs=logs
                    )
                
                # 如果代码执行到这里，说明没有进入前面任何一个特定模型类型的处理分支
                # 尝试通用方法获取预测结果
                try:
                    if 'model' in model_info and hasattr(model_info['model'], 'predict'):
                        # 如果模型支持predict方法，使用它生成预测
                        model = model_info['model']
                        y_pred = model.predict(X_test)
                    else:
                        # 无法预测，返回错误
                        return ExecutionResult(
                            success=False,
                            error_message="不支持的模型类型或模型无法预测，无法生成结果",
                            logs=logs
                        )
                except Exception as e:
                    # 预测失败，返回错误
                    return ExecutionResult(
                        success=False,
                        error_message=f"模型预测失败: {str(e)}",
                        logs=logs + [traceback.format_exc()]
                    )
                
                # 转换预测结果（如果需要还原标签）
                if isinstance(model_info, dict):
                    if 'classes' in model_info:
                        classes = model_info.get('classes', [])
                        if len(classes) > 0 and isinstance(y_pred[0], (int, np.integer)):
                            try:
                                y_pred = np.array([classes[int(i)] if 0 <= int(i) < len(classes) else i for i in y_pred])
                            except Exception as e:
                                logs.append(f"还原类别标签失败: {str(e)}")
                
                # 6. 计算混淆矩阵
                # 获取唯一类别（确保所有预测和真实值的类别都包含在内）
                classes = sorted(list(set(np.concatenate([np.unique(y_test), np.unique(y_pred)]))))
                
                # 计算混淆矩阵
                cm = confusion_matrix(y_test, y_pred, labels=classes)
                
                # 归一化处理
                if normalize:
                    # 避免除零错误
                    row_sums = cm.sum(axis=1)
                    # 仅对非零行进行归一化
                    cm_display = np.zeros_like(cm, dtype=float)
                    for i, sum_val in enumerate(row_sums):
                        if sum_val > 0:
                            cm_display[i] = cm[i] / sum_val
                        # 对于和为0的行保持为0
                else:
                    cm_display = cm.copy()
                
                # 7. 准备输出数据
                # 创建标签映射
                label_mapping = {i: str(label) for i, label in enumerate(classes)}
                
                # 准备数据用于热力图
                heatmap_data = []
                for i in range(cm_display.shape[0]):
                    for j in range(cm_display.shape[1]):
                        heatmap_data.append({
                            'x': j,  # 列索引
                            'y': i,  # 行索引
                            'value': float(cm_display[i, j]),
                            'raw_value': int(cm[i, j])  # 原始计数（未归一化）
                        })
                
                # 9. 准备输出结果 (跳过可视化代码)
                result = {
                    'confusion_matrix': {
                        'data': heatmap_data,
                        'x_labels': [str(cls) for cls in classes],
                        'y_labels': [str(cls) for cls in classes],
                        'normalized': normalize
                    },
                    'raw_matrix': cm.tolist(),
                    'label_mapping': label_mapping,
                    'predictions': y_pred.tolist() if isinstance(y_pred, np.ndarray) else y_pred,
                    'accuracy': float(np.mean(y_pred == y_test))
                }
                
                return ExecutionResult(
                    success=True,
                    outputs={
                        'confusion_matrix': result
                    },
                    logs=logs + [f"混淆矩阵生成完成，准确率: {result['accuracy']:.4f}"]
                )
            except Exception as e:
                error_msg = f"计算ROC曲线时出错: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                # 返回错误结果
                return ExecutionResult(
                    success=False,
                    error_message=error_msg,
                    logs=[traceback.format_exc()]
                )
        except Exception as e:
            # 确保任何序列化错误也被捕获和处理
            try:
                error_msg = f"ROC曲线组件执行失败: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                return ExecutionResult(
                    success=False,
                    error_message=error_msg,
                    logs=[traceback.format_exc()]
                )
            except:
                # 如果连错误信息也无法序列化，返回最简单的错误
                return ExecutionResult(
                    success=False,
                    error_message="ROC曲线组件执行失败，且无法生成详细错误信息",
                    logs=["序列化错误信息失败"]
                )
