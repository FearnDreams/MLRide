"""
组件注册表模块

该模块负责管理所有可用的组件执行器，提供组件的注册和查询功能。
"""

import logging
import importlib
from typing import Dict, Any, Type, Optional
from .executors import BaseComponentExecutor, PythonScriptExecutor
from .data_components import (
    CSVDataLoader, ExcelDataLoader, JSONDataLoader, RandomDataGenerator,
    DataCleaner
)
from .feature_components import (
    FeatureTransformer, FeatureSelector, DataSplitter,
    LabelEncoder, OneHotEncoder, StandardScaler, MinMaxScaler,
    CategoricalEncoder, FeatureEngineer, TextFeatureEngineering, NumericFeatureEngineering
)
from .model_components import (
    LogisticRegressionTrainer, RandomForestTrainer
)

from .evaluation_components import (
    ROCCurveGenerator, ConfusionMatrixGenerator
)
from .visualization_components import (
    BarChartGenerator, LineChartGenerator, HeatmapGenerator
)

logger = logging.getLogger(__name__)

# 组件类型映射，将组件ID和类型映射到对应的执行器类
COMPONENT_REGISTRY = {
    # 数据输入组件
    'csv-input': {'type': 'data_input', 'executor': CSVDataLoader},
    'excel-input': {'type': 'data_input', 'executor': ExcelDataLoader},
    'json-input': {'type': 'data_input', 'executor': JSONDataLoader},
    'random-data': {'type': 'data_input', 'executor': RandomDataGenerator},
    
    # 数据预处理组件
    'data-cleaning': {'type': 'data_preprocessing', 'executor': DataCleaner},
    'feature-transformer': {'type': 'data_preprocessing', 'executor': FeatureTransformer},
    'feature-selector': {'type': 'data_preprocessing', 'executor': FeatureSelector},
    'data-split': {'type': 'data_preprocessing', 'executor': DataSplitter},
    'label-encoder': {'type': 'data_preprocessing', 'executor': LabelEncoder},
    'one-hot-encoder': {'type': 'data_preprocessing', 'executor': OneHotEncoder},
    'standard-scaler': {'type': 'data_preprocessing', 'executor': StandardScaler},
    'min-max-scaler': {'type': 'data_preprocessing', 'executor': MinMaxScaler},
    'encoding-categorical': {'type': 'data_preprocessing', 'executor': CategoricalEncoder},
    'feature-engineering': {'type': 'data_preprocessing', 'executor': FeatureEngineer},
    'text-feature-engineering': {'type': 'data_preprocessing', 'executor': TextFeatureEngineering},
    'numeric-feature-engineering': {'type': 'data_preprocessing', 'executor': NumericFeatureEngineering},
    
    # 模型训练组件
    'logistic-regression': {'type': 'model_training', 'executor': LogisticRegressionTrainer},
    'random-forest': {'type': 'model_training', 'executor': RandomForestTrainer},
    
    # 模型评估组件
    'confusion-matrix': {'type': 'model_evaluation', 'executor': ConfusionMatrixGenerator},
    'roc-curve': {'type': 'model_evaluation', 'executor': ROCCurveGenerator},
    
    # 可视化组件
    'bar-chart': {'type': 'visualization', 'executor': BarChartGenerator},
    'line-chart': {'type': 'visualization', 'executor': LineChartGenerator},
    'heatmap': {'type': 'visualization', 'executor': HeatmapGenerator},
    
    # 自定义组件
    'python-script': {'type': 'custom', 'executor': PythonScriptExecutor},
}


def register_component(component_id: str, component_type: str, executor_class: Type[BaseComponentExecutor]) -> None:
    """
    注册新的组件执行器
    
    Args:
        component_id: 组件ID
        component_type: 组件类型
        executor_class: 执行器类
    """
    COMPONENT_REGISTRY[component_id] = {
        'type': component_type,
        'executor': executor_class
    }


def get_component_executor(component_id: str, component_type: str, container_id: str) -> Optional[BaseComponentExecutor]:
    """
    获取组件执行器实例
    
    根据组件ID和类型获取对应的执行器实例。如果找不到匹配的执行器，尝试使用通用执行器。
    
    Args:
        component_id: 组件ID
        component_type: 组件类型
        container_id: Docker容器ID
        
    Returns:
        BaseComponentExecutor: 组件执行器实例，如果找不到则返回None
    """
    try:
        # 首先根据组件ID尝试获取
        if component_id in COMPONENT_REGISTRY:
            executor_class = COMPONENT_REGISTRY[component_id]['executor']
            return executor_class(component_id, component_type, container_id)
        
        # 如果找不到匹配的ID，尝试找该类型的通用处理器
        for reg_id, reg_info in COMPONENT_REGISTRY.items():
            if reg_info['type'] == component_type and reg_id.endswith('_generic'):
                executor_class = reg_info['executor']
                return executor_class(component_id, component_type, container_id)
        
        # 如果还找不到，使用Python脚本执行器作为通用执行器
        logger.warning(f"找不到组件 {component_id} ({component_type}) 的执行器，将使用通用执行器")
        return PythonScriptExecutor(component_id, component_type, container_id)
        
    except Exception as e:
        logger.error(f"获取组件执行器失败: {str(e)}")
        return None
