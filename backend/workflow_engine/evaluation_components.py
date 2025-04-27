"""
模型评估组件执行器

该模块实现了用于评估机器学习模型性能的组件执行器，如分类指标、回归指标、混淆矩阵、ROC曲线等。
"""

import logging
import json
import traceback
import base64
from typing import Dict, Any, List
from .executors import BaseComponentExecutor, ExecutionResult

logger = logging.getLogger(__name__)

class ClassificationMetrics(BaseComponentExecutor):
    """分类指标计算器
    
    计算分类模型的性能指标，如准确率、精确率、召回率、F1分数等。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        计算分类指标
        
        Args:
            inputs: 输入数据，包括:
                - predictions: 预测结果
                - model: 模型信息（可选）
            parameters: 参数，包括:
                - average: 多分类指标的平均方式（micro, macro, weighted等）
                
        Returns:
            ExecutionResult: 执行结果，包含计算的指标
        """
        try:
            # 获取输入数据
            if 'test_results' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少预测结果"
                )
            
            test_results = inputs['test_results']
            model = inputs.get('model', {})
            
            # 获取参数
            average = parameters.get('average', 'weighted')
            
            # 检查是否是分类问题
            if model.get('problem_type') != 'classification' and model.get('type', '').endswith('classification'):
                return ExecutionResult(
                    success=False,
                    error_message="该组件只适用于分类问题"
                )
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
    from sklearn.metrics import roc_auc_score, roc_curve, auc, precision_recall_curve, average_precision_score
    import matplotlib.pyplot as plt
    import io
    import base64
    
    # 解析测试结果
    test_results = {json.dumps(test_results)}
    predictions = test_results.get('predictions', [])
    probabilities = test_results.get('probabilities', None)
    metrics = test_results.get('metrics', {{}})
    
    # 解析预测数据框
    predictions_df_json = test_results.get('predictions_df', '')
    if predictions_df_json:
        predictions_df = pd.read_json(predictions_df_json, orient='split')
    else:
        predictions_df = None
    
    # 获取实际目标值和预测值
    if predictions_df is not None and 'prediction' in predictions_df.columns:
        # 检查是否有目标列
        target_col = '{parameters.get('target', '')}'
        if not target_col and predictions_df.columns.str.startswith('prob_').any():
            # 推断目标列（去除prob_前缀的列可能是目标列）
            prob_cols = [col for col in predictions_df.columns if col.startswith('prob_')]
            candidate_cols = [col.replace('prob_', '') for col in prob_cols]
            for col in candidate_cols:
                if col in predictions_df.columns:
                    target_col = col
                    break
        
        if target_col and target_col in predictions_df.columns:
            true_values = predictions_df[target_col].values
            predicted_values = predictions_df['prediction'].values
            
            # 计算分类指标
            report = classification_report(true_values, predicted_values, output_dict=True)
            
            # 详细指标
            detailed_metrics = {{
                'accuracy': float(accuracy_score(true_values, predicted_values)),
                'precision': float(precision_score(true_values, predicted_values, average='{average}', zero_division=0)),
                'recall': float(recall_score(true_values, predicted_values, average='{average}', zero_division=0)),
                'f1': float(f1_score(true_values, predicted_values, average='{average}', zero_division=0)),
                'classification_report': report
            }}
            
            # 生成每个类别的指标
            class_metrics = {{}}
            for class_name, metrics_dict in report.items():
                if class_name not in ['accuracy', 'macro avg', 'weighted avg', 'samples avg']:
                    class_metrics[class_name] = {{
                        'precision': metrics_dict['precision'],
                        'recall': metrics_dict['recall'],
                        'f1-score': metrics_dict['f1-score'],
                        'support': metrics_dict['support']
                    }}
            
            # 计算ROC和PR曲线（仅适用于二分类）
            curves = {{}}
            if len(np.unique(true_values)) == 2 and 'probability' in predictions_df.columns:
                # ROC曲线
                fpr, tpr, thresholds = roc_curve(true_values, predictions_df['probability'].values)
                roc_auc = auc(fpr, tpr)
                
                # 绘制ROC曲线
                plt.figure(figsize=(8, 6))
                plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {{roc_auc:.2f}})')
                plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
                plt.xlim([0.0, 1.0])
                plt.ylim([0.0, 1.05])
                plt.xlabel('False Positive Rate')
                plt.ylabel('True Positive Rate')
                plt.title('Receiver Operating Characteristic (ROC) Curve')
                plt.legend(loc='lower right')
                
                # 保存图像为base64
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                roc_curve_img = base64.b64encode(buf.read()).decode('utf-8')
                plt.close()
                
                # PR曲线
                precision, recall, thresholds = precision_recall_curve(true_values, predictions_df['probability'].values)
                pr_auc = average_precision_score(true_values, predictions_df['probability'].values)
                
                # 绘制PR曲线
                plt.figure(figsize=(8, 6))
                plt.plot(recall, precision, color='blue', lw=2, label=f'PR curve (area = {{pr_auc:.2f}})')
                plt.xlim([0.0, 1.0])
                plt.ylim([0.0, 1.05])
                plt.xlabel('Recall')
                plt.ylabel('Precision')
                plt.title('Precision-Recall Curve')
                plt.legend(loc='lower left')
                
                # 保存图像为base64
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                pr_curve_img = base64.b64encode(buf.read()).decode('utf-8')
                plt.close()
                
                curves = {{
                    'roc': {{
                        'fpr': fpr.tolist(),
                        'tpr': tpr.tolist(),
                        'thresholds': thresholds.tolist(),
                        'auc': float(roc_auc),
                        'image': roc_curve_img
                    }},
                    'pr': {{
                        'precision': precision.tolist(),
                        'recall': recall.tolist(),
                        'thresholds': thresholds.tolist() if len(thresholds) == len(precision) else thresholds.tolist() + [0],
                        'auc': float(pr_auc),
                        'image': pr_curve_img
                    }}
                }}
            
            result = {{
                'metrics': detailed_metrics,
                'class_metrics': class_metrics,
                'curves': curves
            }}
        else:
            # 没有目标列，只能返回预测分布
            result = {{
                'metrics': metrics
            }}
    else:
        # 没有预测数据框，直接返回测试结果中的指标
        result = {{
            'metrics': metrics
        }}
except Exception as e:
    raise Exception(f"计算分类指标失败: {{str(e)}}")
"""
            
            # 在容器中执行
            exec_result = self.execute_in_container(code)
            
            if exec_result.get('success', False):
                result = exec_result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs=result,
                    logs=["分类指标计算完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=exec_result.get('error', '计算分类指标失败'),
                    logs=[exec_result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行分类指标计算器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class RegressionMetrics(BaseComponentExecutor):
    """回归指标计算器
    
    计算回归模型的性能指标，如均方误差、平均绝对误差、R²等。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        计算回归指标
        
        Args:
            inputs: 输入数据，包括:
                - predictions: 预测结果
                - model: 模型信息（可选）
                
        Returns:
            ExecutionResult: 执行结果，包含计算的指标
        """
        try:
            # 获取输入数据
            if 'test_results' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少预测结果"
                )
            
            test_results = inputs['test_results']
            model = inputs.get('model', {})
            
            # 检查是否是回归问题
            if model.get('problem_type') == 'classification' or model.get('type', '').endswith('classification'):
                return ExecutionResult(
                    success=False,
                    error_message="该组件只适用于回归问题"
                )
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, explained_variance_score
    import matplotlib.pyplot as plt
    import io
    import base64
    
    # 解析测试结果
    test_results = {json.dumps(test_results)}
    predictions = test_results.get('predictions', [])
    metrics = test_results.get('metrics', {{}})
    
    # 解析预测数据框
    predictions_df_json = test_results.get('predictions_df', '')
    if predictions_df_json:
        predictions_df = pd.read_json(predictions_df_json, orient='split')
    else:
        predictions_df = None
    
    # 获取实际目标值和预测值
    if predictions_df is not None and 'prediction' in predictions_df.columns:
        # 检查是否有目标列
        target_col = '{parameters.get('target', '')}'
        if not target_col:
            # 尝试推断目标列，通常是模型输出中的prediction除外的另一列
            for col in predictions_df.columns:
                if col != 'prediction' and pd.api.types.is_numeric_dtype(predictions_df[col]):
                    target_col = col
                    break
        
        if target_col and target_col in predictions_df.columns:
            true_values = predictions_df[target_col].values
            predicted_values = predictions_df['prediction'].values
            
            # 计算回归指标
            mse = mean_squared_error(true_values, predicted_values)
            rmse = np.sqrt(mse)
            mae = mean_absolute_error(true_values, predicted_values)
            r2 = r2_score(true_values, predicted_values)
            explained_variance = explained_variance_score(true_values, predicted_values)
            
            # 计算残差
            residuals = true_values - predicted_values
            
            # 详细指标
            detailed_metrics = {{
                'mse': float(mse),
                'rmse': float(rmse),
                'mae': float(mae),
                'r2': float(r2),
                'explained_variance': float(explained_variance)
            }}
            
            # 生成散点图和残差图
            plots = {{}}
            
            # 预测值与实际值的散点图
            plt.figure(figsize=(8, 6))
            plt.scatter(true_values, predicted_values, alpha=0.5)
            plt.plot([true_values.min(), true_values.max()], [true_values.min(), true_values.max()], 'k--', lw=2)
            plt.xlabel('True Values')
            plt.ylabel('Predictions')
            plt.title('Predicted vs True Values')
            
            # 保存图像为base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            scatter_img = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            # 残差图
            plt.figure(figsize=(8, 6))
            plt.scatter(predicted_values, residuals, alpha=0.5)
            plt.hlines(y=0, xmin=predicted_values.min(), xmax=predicted_values.max(), colors='k', linestyles='--')
            plt.xlabel('Predicted Values')
            plt.ylabel('Residuals')
            plt.title('Residuals vs Predicted Values')
            
            # 保存图像为base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            residuals_img = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            # 残差直方图
            plt.figure(figsize=(8, 6))
            plt.hist(residuals, bins=30, alpha=0.7, color='blue')
            plt.xlabel('Residuals')
            plt.ylabel('Frequency')
            plt.title('Residuals Distribution')
            
            # 保存图像为base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            residuals_hist_img = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            plots = {{
                'scatter': scatter_img,
                'residuals': residuals_img,
                'residuals_hist': residuals_hist_img
            }}
            
            result = {{
                'metrics': detailed_metrics,
                'plots': plots,
                'residuals_stats': {{
                    'mean': float(np.mean(residuals)),
                    'std': float(np.std(residuals)),
                    'min': float(np.min(residuals)),
                    'max': float(np.max(residuals)),
                    'q1': float(np.percentile(residuals, 25)),
                    'median': float(np.median(residuals)),
                    'q3': float(np.percentile(residuals, 75))
                }}
            }}
        else:
            # 没有目标列，只能返回预测分布
            result = {{
                'metrics': metrics
            }}
    else:
        # 没有预测数据框，直接返回测试结果中的指标
        result = {{
            'metrics': metrics
        }}
except Exception as e:
    raise Exception(f"计算回归指标失败: {{str(e)}}")
"""
            
            # 在容器中执行
            exec_result = self.execute_in_container(code)
            
            if exec_result.get('success', False):
                result = exec_result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs=result,
                    logs=["回归指标计算完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=exec_result.get('error', '计算回归指标失败'),
                    logs=[exec_result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行回归指标计算器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class ConfusionMatrix(BaseComponentExecutor):
    """混淆矩阵生成器
    
    生成分类模型的混淆矩阵，用于评估模型性能。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成混淆矩阵
        
        Args:
            inputs: 输入数据，包括:
                - predictions: 预测结果
                - model: 模型信息（可选）
            parameters: 参数，包括:
                - normalize: 是否归一化（true/false）
                
        Returns:
            ExecutionResult: 执行结果，包含混淆矩阵
        """
        try:
            # 获取输入数据
            if 'test_results' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少预测结果"
                )
            
            test_results = inputs['test_results']
            model = inputs.get('model', {})
            
            # 获取参数
            normalize = parameters.get('normalize', 'false') == 'true'
            
            # 检查是否是分类问题
            if model.get('problem_type') != 'classification' and model.get('type', '').endswith('classification'):
                return ExecutionResult(
                    success=False,
                    error_message="该组件只适用于分类问题"
                )
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
    import matplotlib.pyplot as plt
    import seaborn as sns
    import io
    import base64
    
    # 解析测试结果
    test_results = {json.dumps(test_results)}
    predictions = test_results.get('predictions', [])
    
    # 解析预测数据框
    predictions_df_json = test_results.get('predictions_df', '')
    if predictions_df_json:
        predictions_df = pd.read_json(predictions_df_json, orient='split')
    else:
        predictions_df = None
    
    # 获取实际目标值和预测值
    if predictions_df is not None and 'prediction' in predictions_df.columns:
        # 检查是否有目标列
        target_col = '{parameters.get('target', '')}'
        if not target_col:
            # 尝试推断目标列
            for col in predictions_df.columns:
                if col != 'prediction' and not col.startswith('prob_'):
                    target_col = col
                    break
        
        if target_col and target_col in predictions_df.columns:
            true_values = predictions_df[target_col].values
            predicted_values = predictions_df['prediction'].values
            
            # 获取类别标签
            classes = sorted(list(set(np.concatenate([np.unique(true_values), np.unique(predicted_values)]))))
            
            # 计算混淆矩阵
            cm = confusion_matrix(true_values, predicted_values, labels=classes)
            
            # 如果需要归一化
            if {normalize}:
                cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
                cm_display = cm_normalized
                vmin, vmax = 0, 1
            else:
                cm_display = cm
                vmin, vmax = None, None
            
            # 绘制混淆矩阵
            plt.figure(figsize=(10, 8))
            sns.heatmap(cm_display, annot=True, fmt='.2f' if {normalize} else 'd', 
                      cmap='Blues', xticklabels=classes, yticklabels=classes,
                      vmin=vmin, vmax=vmax)
            plt.xlabel('Predicted Label')
            plt.ylabel('True Label')
            plt.title('Confusion Matrix')
            
            # 保存图像为base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            cm_img = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            result = {{
                'confusion_matrix': cm.tolist(),
                'classes': classes,
                'normalized': {normalize},
                'image': cm_img
            }}
        else:
            raise ValueError(f"找不到目标列 {{target_col if target_col else '(自动推断)'}} 在预测数据框中")
    else:
        raise ValueError("预测结果中找不到预测数据框或没有prediction列")
except Exception as e:
    raise Exception(f"生成混淆矩阵失败: {{str(e)}}")
"""
            
            # 在容器中执行
            exec_result = self.execute_in_container(code)
            
            if exec_result.get('success', False):
                result = exec_result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs=result,
                    logs=["混淆矩阵生成完成"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=exec_result.get('error', '生成混淆矩阵失败'),
                    logs=[exec_result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行混淆矩阵生成器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class ROCCurveGenerator(BaseComponentExecutor):
    """ROC曲线生成器
    
    生成分类模型的ROC曲线和AUC指标，用于评估模型性能。
    对应前端组件ID: roc-curve
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成ROC曲线
        
        Args:
            inputs: 输入数据，包括:
                - model: 训练好的模型
                - test: 测试数据集
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标列
                - class_names: 类别名称
                
        Returns:
            ExecutionResult: 执行结果，包含ROC曲线图像和AUC值
        """
        try:
            # 获取输入数据
            if 'model' not in inputs or 'test' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少模型或测试数据"
                )
            
            model = inputs['model']
            test_data = inputs['test']
            
            # 获取参数
            features = parameters.get('features', '')
            target = parameters.get('target', '')
            
            # 检查参数
            if not features or not target:
                return ExecutionResult(
                    success=False,
                    error_message="缺少特征列或目标列参数"
                )
                
            if isinstance(features, str):
                features = [f.strip() for f in features.split(',') if f.strip()]
            
            # 生成Python代码
            code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import json
import pickle
from sklearn.metrics import roc_curve, auc, roc_auc_score
from sklearn.preprocessing import label_binarize

# 加载数据和模型
test_data = pd.read_json(r'''{}''')
model_data = r'''{}'''
model = pickle.loads(bytes.fromhex(model_data))

# 获取特征和目标
features = {}
target = '{}'

# 检查特征和目标列是否存在
missing_features = [col for col in features if col not in test_data.columns]
if missing_features:
    raise ValueError(f"以下特征列不存在于测试数据中: {{missing_features}}")

if target not in test_data.columns:
    raise ValueError(f"目标列 '{target}' 不存在于测试数据中")

# 准备数据
X_test = test_data[features]
y_test = test_data[target]

# 判断是二分类还是多分类
classes = np.unique(y_test)
n_classes = len(classes)

plt.figure(figsize=(10, 8))

result = {{
    'auc': [],
    'image': '',
    'classes': classes.tolist(),
    'is_multiclass': n_classes > 2
}}

try:
    if hasattr(model, 'predict_proba'):
        # 使用predict_proba获取预测概率
        if n_classes == 2:
            # 二分类
            y_score = model.predict_proba(X_test)[:, 1]
            
            # 计算ROC曲线和AUC
            fpr, tpr, _ = roc_curve(y_test, y_score)
            roc_auc = auc(fpr, tpr)
            
            # 绘制ROC曲线
            plt.plot(fpr, tpr, lw=2, label=f'ROC曲线 (AUC = {{roc_auc:.3f}})')
            plt.plot([0, 1], [0, 1], 'k--', lw=2)
            
            result['auc'] = [float(roc_auc)]
            
        else:
            # 多分类
            # 对标签进行二进制化
            y_test_bin = label_binarize(y_test, classes=classes)
            
            # 获取每个类别的预测概率
            y_score = model.predict_proba(X_test)
            
            # 为每个类别计算ROC曲线和AUC
            for i, class_name in enumerate(classes):
                fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_score[:, i])
                roc_auc = auc(fpr, tpr)
                
                # 绘制ROC曲线
                plt.plot(fpr, tpr, lw=2, label=f'ROC曲线 {{class_name}} (AUC = {{roc_auc:.3f}})')
                
                # 添加到结果
                result['auc'].append(float(roc_auc))
            
            # 绘制对角线
            plt.plot([0, 1], [0, 1], 'k--', lw=2)
    else:
        raise ValueError("模型不支持概率预测，无法生成ROC曲线")
    
    # 设置图表属性
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('假正例率 (FPR)')
    plt.ylabel('真正例率 (TPR)')
    plt.title('接收者操作特征曲线 (ROC)')
    plt.legend(loc="lower right")
    plt.grid(True)
    
    # 将图表转换为base64编码的图像
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # 添加到结果
    result['image'] = img_base64
    
except Exception as e:
    plt.close()
    raise ValueError(f"生成ROC曲线时出错: {{str(e)}}")

# 输出结果
print(json.dumps(result))
""".format(json.dumps(test_data), model.get('model_data', ''), features, target)
            
            # 执行代码并获取结果
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"ROC曲线生成失败: {output}"
                )
                
            # 解析输出
            result = json.loads(output)
            
            return ExecutionResult(
                success=True,
                output={
                    'auc': result['auc'],
                    'image': result['image'],
                    'classes': result['classes'],
                    'is_multiclass': result['is_multiclass']
                }
            )
            
        except Exception as e:
            error_message = f"ROC曲线生成失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )


class LearningCurveGenerator(BaseComponentExecutor):
    """学习曲线生成器
    
    生成模型的学习曲线，用于评估模型的泛化性能和是否存在过拟合或欠拟合。
    对应前端组件ID: learning-curve
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成学习曲线
        
        Args:
            inputs: 输入数据，包括:
                - train: 训练数据集
            parameters: 参数，包括:
                - features: 特征列
                - target: 目标列
                - model_type: 模型类型
                - cv: 交叉验证折数
                - scoring: 评分方式
                - title: 图表标题
                
        Returns:
            ExecutionResult: 执行结果，包含学习曲线图像
        """
        try:
            # 获取输入数据
            if 'train' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少训练数据"
                )
            
            train_data = inputs['train']
            
            # 获取参数
            features = parameters.get('features', '')
            target = parameters.get('target', '')
            model_type = parameters.get('model_type', 'linear')
            cv = parameters.get('cv', 5)
            scoring = parameters.get('scoring', 'accuracy')
            title = parameters.get('title', '学习曲线')
            
            # 检查参数
            if not features or not target:
                return ExecutionResult(
                    success=False,
                    error_message="缺少特征列或目标列参数"
                )
                
            if isinstance(features, str):
                features = [f.strip() for f in features.split(',') if f.strip()]
            
            # 生成Python代码
            code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import json
from sklearn.model_selection import learning_curve
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVC, SVR

# 加载数据
train_data = pd.read_json(r'''{}''')

# 获取特征和目标
features = {}
target = '{}'
model_type = '{}'
cv = {}
scoring = '{}'
title = '{}'

# 检查特征和目标列是否存在
missing_features = [col for col in features if col not in train_data.columns]
if missing_features:
    raise ValueError(f"以下特征列不存在于训练数据中: {{missing_features}}")

if target not in train_data.columns:
    raise ValueError(f"目标列 '{target}' 不存在于训练数据中")

# 准备数据
X = train_data[features]
y = train_data[target]

# 特征标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 根据模型类型选择合适的模型
if model_type == 'linear':
    # 线性回归/逻辑回归
    # 判断是分类还是回归
    if len(np.unique(y)) < 10 and all(isinstance(val, (int, bool)) or val.is_integer() for val in y):
        # 分类问题
        model = LogisticRegression(max_iter=1000)
        problem_type = 'classification'
    else:
        # 回归问题
        model = LinearRegression()
        problem_type = 'regression'
elif model_type == 'tree':
    # 决策树
    if len(np.unique(y)) < 10 and all(isinstance(val, (int, bool)) or val.is_integer() for val in y):
        model = DecisionTreeClassifier()
        problem_type = 'classification'
    else:
        model = DecisionTreeRegressor()
        problem_type = 'regression'
elif model_type == 'forest':
    # 随机森林
    if len(np.unique(y)) < 10 and all(isinstance(val, (int, bool)) or val.is_integer() for val in y):
        model = RandomForestClassifier()
        problem_type = 'classification'
    else:
        model = RandomForestRegressor()
        problem_type = 'regression'
elif model_type == 'svm':
    # 支持向量机
    if len(np.unique(y)) < 10 and all(isinstance(val, (int, bool)) or val.is_integer() for val in y):
        model = SVC(probability=True)
        problem_type = 'classification'
    else:
        model = SVR()
        problem_type = 'regression'
else:
    raise ValueError(f"不支持的模型类型: {{model_type}}")

# 确定评分方式
if scoring == 'auto':
    if problem_type == 'classification':
        scoring = 'accuracy'
    else:
        scoring = 'neg_mean_squared_error'

# 计算学习曲线
train_sizes = np.linspace(0.1, 1.0, 10)
train_sizes, train_scores, test_scores = learning_curve(
    model, X_scaled, y, 
    cv=cv, 
    scoring=scoring,
    train_sizes=train_sizes,
    n_jobs=-1,
    shuffle=True,
    random_state=42
)

# 计算平均值和标准差
train_scores_mean = np.mean(train_scores, axis=1)
train_scores_std = np.std(train_scores, axis=1)
test_scores_mean = np.mean(test_scores, axis=1)
test_scores_std = np.std(test_scores, axis=1)

# 创建图表
plt.figure(figsize=(10, 6))

# 绘制训练得分和测试得分
plt.fill_between(train_sizes, train_scores_mean - train_scores_std,
                 train_scores_mean + train_scores_std, alpha=0.1, color="r")
plt.fill_between(train_sizes, test_scores_mean - test_scores_std,
                 test_scores_mean + test_scores_std, alpha=0.1, color="g")
plt.plot(train_sizes, train_scores_mean, 'o-', color="r", label="训练得分")
plt.plot(train_sizes, test_scores_mean, 'o-', color="g", label="交叉验证得分")

# 设置图表属性
plt.title(title)
plt.xlabel("训练样本数")
plt.ylabel(f"得分 ({scoring})")
plt.legend(loc="best")
plt.grid(True)

# 将图表转换为base64编码的图像
buf = io.BytesIO()
plt.savefig(buf, format='png', dpi=100)
buf.seek(0)
img_base64 = base64.b64encode(buf.read()).decode('utf-8')
plt.close()

# 准备结果
result = {{
    'image': img_base64,
    'train_sizes': train_sizes.tolist(),
    'train_scores': train_scores_mean.tolist(),
    'test_scores': test_scores_mean.tolist(),
    'model_type': model_type,
    'problem_type': problem_type,
    'scoring': scoring
}}

# 输出结果
print(json.dumps(result))
""".format(json.dumps(train_data), features, target, model_type, cv, scoring, title)
            
            # 执行代码并获取结果
            success, output = self.execute_in_container(code)
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=f"学习曲线生成失败: {output}"
                )
                
            # 解析输出
            result = json.loads(output)
            
            return ExecutionResult(
                success=True,
                output=result
            )
            
        except Exception as e:
            error_message = f"学习曲线生成失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return ExecutionResult(
                success=False,
                error_message=error_message
            )
