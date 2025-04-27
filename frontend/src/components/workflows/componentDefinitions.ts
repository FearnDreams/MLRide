/**
 * 工作流组件定义
 * 
 * 这个文件包含了可视化拖拽编程模块中所有可用的组件定义
 */

import { ComponentDefinition, ComponentType, ComponentCategory, DataType } from '@/store/workflowStore';

// -----------------------------
// 数据输入组件
// -----------------------------
export const dataInputComponents: ComponentDefinition[] = [
  {
    id: 'csv-input',
    type: ComponentType.INPUT,
    category: ComponentCategory.DATA_INPUT,
    name: 'CSV数据输入',
    description: '从CSV文件加载数据',
    color: '#4caf50',
    icon: 'FileText',
    inputs: [],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '数据集' }
    ],
    params: [
      {
        name: 'source',
        label: '数据来源',
        type: 'select',
        options: [
          { value: 'upload', label: '上传文件' },
          { value: 'dataset', label: '已有数据集' }
        ],
        defaultValue: 'upload',
        required: true
      },
      {
        name: 'file_path',
        label: '文件路径',
        type: 'file',
        description: '选择要上传的CSV文件',
        required: false
      },
      {
        name: 'dataset_name',
        label: '数据集名称',
        type: 'string',
        placeholder: '请输入数据集名称',
        required: false
      },
      {
        name: 'has_header',
        label: '包含表头',
        type: 'boolean',
        defaultValue: true
      },
      {
        name: 'separator',
        label: '分隔符',
        type: 'select',
        options: [
          { value: ',', label: '逗号 (,)' },
          { value: ';', label: '分号 (;)' },
          { value: '\\t', label: '制表符 (\\t)' },
          { value: ' ', label: '空格 ( )' }
        ],
        defaultValue: ','
      }
    ],
    defaultParams: {
      source: 'upload',
      file_path: '',
      dataset_name: '',
      has_header: true,
      separator: ','
    }
  },
  {
    id: 'excel-input',
    type: ComponentType.INPUT,
    category: ComponentCategory.DATA_INPUT,
    name: 'Excel数据输入',
    description: '从Excel文件加载数据',
    color: '#4caf50',
    icon: 'FileSpreadsheet',
    inputs: [],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '数据集' }
    ],
    params: [
      {
        name: 'source',
        label: '数据来源',
        type: 'select',
        options: [
          { value: 'upload', label: '上传文件' },
          { value: 'dataset', label: '已有数据集' }
        ],
        defaultValue: 'upload',
        required: true
      },
      {
        name: 'file_path',
        label: '文件路径',
        type: 'file',
        description: '选择要上传的Excel文件',
        required: false
      },
      {
        name: 'dataset_name',
        label: '数据集名称',
        type: 'string',
        placeholder: '请输入数据集名称',
        required: false
      },
      {
        name: 'sheet_name',
        label: '工作表名称',
        type: 'string',
        placeholder: '留空将使用第一个工作表',
        required: false
      },
      {
        name: 'has_header',
        label: '包含表头',
        type: 'boolean',
        defaultValue: true
      }
    ],
    defaultParams: {
      source: 'upload',
      file_path: '',
      dataset_name: '',
      sheet_name: '',
      has_header: true
    }
  },
  {
    id: 'database-input',
    type: ComponentType.INPUT,
    category: ComponentCategory.DATA_INPUT,
    name: '数据库输入',
    description: '从数据库加载数据',
    color: '#4caf50',
    icon: 'Database',
    inputs: [],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '数据集' }
    ],
    params: [
      {
        name: 'db_type',
        label: '数据库类型',
        type: 'select',
        options: [
          { value: 'mysql', label: 'MySQL' },
          { value: 'postgresql', label: 'PostgreSQL' },
          { value: 'sqlite', label: 'SQLite' }
        ],
        defaultValue: 'mysql',
        required: true
      },
      {
        name: 'host',
        label: '主机地址',
        type: 'string',
        placeholder: '如: localhost',
        required: false
      },
      {
        name: 'port',
        label: '端口',
        type: 'number',
        defaultValue: 3306,
        required: false
      },
      {
        name: 'username',
        label: '用户名',
        type: 'string',
        required: false
      },
      {
        name: 'password',
        label: '密码',
        type: 'string',
        required: false
      },
      {
        name: 'database',
        label: '数据库名',
        type: 'string',
        required: false
      },
      {
        name: 'query',
        label: 'SQL查询',
        type: 'text',
        placeholder: '输入SQL查询语句',
        required: false
      }
    ],
    defaultParams: {
      db_type: 'mysql',
      host: 'localhost',
      port: 3306,
      username: '',
      password: '',
      database: '',
      query: 'SELECT * FROM table_name'
    }
  },
  {
    id: 'json-input',
    type: ComponentType.INPUT,
    category: ComponentCategory.DATA_INPUT,
    name: 'JSON数据输入',
    description: '从JSON文件加载数据',
    color: '#4caf50',
    icon: 'Code',
    inputs: [],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '数据集' }
    ],
    params: [
      {
        name: 'source',
        label: '数据来源',
        type: 'select',
        options: [
          { value: 'upload', label: '上传文件' },
          { value: 'dataset', label: '已有数据集' },
          { value: 'raw', label: '原始JSON' }
        ],
        defaultValue: 'upload',
        required: true
      },
      {
        name: 'file_path',
        label: '文件路径',
        type: 'file',
        description: '选择要上传的JSON文件',
        required: false
      },
      {
        name: 'dataset_name',
        label: '数据集名称',
        type: 'string',
        placeholder: '请输入数据集名称',
        required: false
      },
      {
        name: 'json_content',
        label: 'JSON内容',
        type: 'text',
        placeholder: '输入JSON数据',
        required: false
      },
      {
        name: 'orientation',
        label: '数据方向',
        type: 'select',
        options: [
          { value: 'records', label: '记录列表' },
          { value: 'columns', label: '列字典' },
          { value: 'index', label: '索引字典' }
        ],
        defaultValue: 'records'
      }
    ],
    defaultParams: {
      source: 'upload',
      file_path: '',
      dataset_name: '',
      json_content: '',
      orientation: 'records'
    }
  },
  {
    id: 'random-data',
    type: ComponentType.INPUT,
    category: ComponentCategory.DATA_INPUT,
    name: '随机数据生成',
    description: '生成随机测试数据',
    color: '#4caf50',
    icon: 'Dice',
    inputs: [],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '随机数据' }
    ],
    params: [
      {
        name: 'rows',
        label: '行数',
        type: 'number',
        min: 1,
        max: 10000,
        defaultValue: 100
      },
      {
        name: 'data_type',
        label: '数据类型',
        type: 'select',
        options: [
          { value: 'classification', label: '分类数据' },
          { value: 'regression', label: '回归数据' },
          { value: 'clustering', label: '聚类数据' },
          { value: 'random', label: '完全随机' }
        ],
        defaultValue: 'regression'
      },
      {
        name: 'features',
        label: '特征数',
        type: 'number',
        min: 1,
        max: 100,
        defaultValue: 5
      },
      {
        name: 'classes',
        label: '类别数(分类)',
        type: 'number',
        min: 2,
        max: 10,
        defaultValue: 2
      },
      {
        name: 'random_state',
        label: '随机种子',
        type: 'number',
        defaultValue: 42
      }
    ],
    defaultParams: {
      rows: 100,
      data_type: 'regression',
      features: 5,
      classes: 2,
      random_state: 42
    }
  }
];

// -----------------------------
// 数据预处理组件
// -----------------------------
export const dataProcessingComponents: ComponentDefinition[] = [
  {
    id: 'data-cleaning',
    type: ComponentType.PROCESS,
    category: ComponentCategory.DATA_PREPROCESSING,
    name: '数据清洗',
    description: '清理数据中的缺失值、异常值等',
    color: '#2196f3',
    icon: 'Filter',
    inputs: [
      { id: 'input', type: DataType.DATAFRAME, label: '输入数据' }
    ],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '清洗后数据' }
    ],
    params: [
      {
        name: 'handle_missing',
        label: '处理缺失值',
        type: 'select',
        options: [
          { value: 'drop_rows', label: '删除包含缺失值的行' },
          { value: 'drop_columns', label: '删除包含缺失值的列' },
          { value: 'fill_mean', label: '用均值填充' },
          { value: 'fill_median', label: '用中位数填充' },
          { value: 'fill_mode', label: '用众数填充' },
          { value: 'fill_constant', label: '用常数填充' },
          { value: 'none', label: '不处理' }
        ],
        defaultValue: 'fill_mean'
      },
      {
        name: 'fill_value',
        label: '填充值',
        type: 'string',
        placeholder: '用于常数填充',
        defaultValue: '0'
      },
      {
        name: 'handle_outliers',
        label: '处理异常值',
        type: 'select',
        options: [
          { value: 'remove', label: '删除异常值' },
          { value: 'cap', label: '限制到分位数范围' },
          { value: 'none', label: '不处理' }
        ],
        defaultValue: 'none'
      },
      {
        name: 'lower_quantile',
        label: '下限分位数',
        type: 'number',
        min: 0,
        max: 0.5,
        step: 0.01,
        defaultValue: 0.05
      },
      {
        name: 'upper_quantile',
        label: '上限分位数',
        type: 'number',
        min: 0.5,
        max: 1,
        step: 0.01,
        defaultValue: 0.95
      }
    ],
    defaultParams: {
      handle_missing: 'fill_mean',
      fill_value: '0',
      handle_outliers: 'none',
      lower_quantile: 0.05,
      upper_quantile: 0.95
    }
  },
  {
    id: 'data-transformation',
    type: ComponentType.PROCESS,
    category: ComponentCategory.DATA_PREPROCESSING,
    name: '数据转换',
    description: '转换、标准化或归一化数据',
    color: '#2196f3',
    icon: 'RefreshCw',
    inputs: [
      { id: 'input', type: DataType.DATAFRAME, label: '输入数据' }
    ],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '转换后数据' }
    ],
    params: [
      {
        name: 'transformation_type',
        label: '转换类型',
        type: 'select',
        options: [
          { value: 'standardize', label: '标准化 (Z-Score)' },
          { value: 'normalize', label: '归一化 (Min-Max)' },
          { value: 'log', label: '对数转换' },
          { value: 'sqrt', label: '平方根转换' },
          { value: 'box-cox', label: 'Box-Cox变换' }
        ],
        defaultValue: 'standardize'
      },
      {
        name: 'columns',
        label: '处理列',
        type: 'string',
        placeholder: '列名，用逗号分隔，留空处理所有数值列',
        defaultValue: ''
      }
    ],
    defaultParams: {
      transformation_type: 'standardize',
      columns: ''
    }
  },
  {
    id: 'feature-selection',
    type: ComponentType.PROCESS,
    category: ComponentCategory.DATA_PREPROCESSING,
    name: '特征选择',
    description: '选择最相关或最重要的特征',
    color: '#2196f3',
    icon: 'CheckSquare',
    inputs: [
      { id: 'input', type: DataType.DATAFRAME, label: '输入数据' }
    ],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '选择后数据' }
    ],
    params: [
      {
        name: 'method',
        label: '选择方法',
        type: 'select',
        options: [
          { value: 'pearson', label: '皮尔逊相关系数' },
          { value: 'chi2', label: '卡方检验' },
          { value: 'mutual_info', label: '互信息' },
          { value: 'variance', label: '低方差过滤' },
          { value: 'rfe', label: '递归特征消除' }
        ],
        defaultValue: 'pearson'
      },
      {
        name: 'target',
        label: '目标变量',
        type: 'string',
        placeholder: '目标列名',
        required: true
      },
      {
        name: 'num_features',
        label: '选择特征数',
        type: 'number',
        min: 1,
        defaultValue: 5
      },
      {
        name: 'threshold',
        label: '阈值',
        type: 'number',
        min: 0,
        max: 1,
        step: 0.01,
        defaultValue: 0.05
      }
    ],
    defaultParams: {
      method: 'pearson',
      target: '',
      num_features: 5,
      threshold: 0.05
    }
  },
  {
    id: 'data-split',
    type: ComponentType.PROCESS,
    category: ComponentCategory.DATA_PREPROCESSING,
    name: '数据集拆分',
    description: '将数据集拆分为训练集和测试集',
    color: '#2196f3',
    icon: 'Scissors',
    inputs: [
      { id: 'input', type: DataType.DATAFRAME, label: '输入数据' }
    ],
    outputs: [
      { id: 'train', type: DataType.DATAFRAME, label: '训练数据' },
      { id: 'test', type: DataType.DATAFRAME, label: '测试数据' }
    ],
    params: [
      {
        name: 'test_size',
        label: '测试集比例',
        type: 'number',
        min: 0.1,
        max: 0.5,
        step: 0.05,
        defaultValue: 0.2
      },
      {
        name: 'stratify',
        label: '分层抽样',
        type: 'boolean',
        defaultValue: false
      },
      {
        name: 'stratify_column',
        label: '分层列',
        type: 'string',
        placeholder: '用于分层的列名',
        required: false
      },
      {
        name: 'random_state',
        label: '随机种子',
        type: 'number',
        defaultValue: 42
      }
    ],
    defaultParams: {
      test_size: 0.2,
      stratify: false,
      stratify_column: '',
      random_state: 42
    }
  },
  {
    id: 'encoding-categorical',
    type: ComponentType.PROCESS,
    category: ComponentCategory.DATA_PREPROCESSING,
    name: '类别特征编码',
    description: '将类别特征转换为数值表示',
    color: '#2196f3',
    icon: 'Tag',
    inputs: [
      { id: 'input', type: DataType.DATAFRAME, label: '输入数据' }
    ],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '编码后数据' }
    ],
    params: [
      {
        name: 'encoding_method',
        label: '编码方法',
        type: 'select',
        options: [
          { value: 'one_hot', label: '独热编码' },
          { value: 'label', label: '标签编码' },
          { value: 'ordinal', label: '序数编码' },
          { value: 'frequency', label: '频率编码' },
          { value: 'binary', label: '二进制编码' }
        ],
        defaultValue: 'one_hot'
      },
      {
        name: 'columns',
        label: '处理列',
        type: 'string',
        placeholder: '列名，用逗号分隔，留空自动检测类别特征',
        defaultValue: ''
      },
      {
        name: 'handle_unknown',
        label: '处理未知值',
        type: 'select',
        options: [
          { value: 'error', label: '报错' },
          { value: 'ignore', label: '忽略' },
          { value: 'use_na', label: '视为缺失值' }
        ],
        defaultValue: 'error'
      }
    ],
    defaultParams: {
      encoding_method: 'one_hot',
      columns: '',
      handle_unknown: 'error'
    }
  },
  {
    id: 'feature-engineering',
    type: ComponentType.PROCESS,
    category: ComponentCategory.DATA_PREPROCESSING,
    name: '特征工程',
    description: '创建新特征或转换现有特征',
    color: '#2196f3',
    icon: 'Tool',
    inputs: [
      { id: 'input', type: DataType.DATAFRAME, label: '输入数据' }
    ],
    outputs: [
      { id: 'output', type: DataType.DATAFRAME, label: '特征工程后数据' }
    ],
    params: [
      {
        name: 'operations',
        label: '特征操作',
        type: 'select',
        options: [
          { value: 'polynomial', label: '多项式特征' },
          { value: 'interaction', label: '交互项' },
          { value: 'binning', label: '特征分箱' },
          { value: 'custom', label: '自定义公式' }
        ],
        defaultValue: 'polynomial'
      },
      {
        name: 'columns',
        label: '处理列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'degree',
        label: '多项式次数',
        type: 'number',
        min: 2,
        max: 5,
        defaultValue: 2
      },
      {
        name: 'n_bins',
        label: '分箱数量',
        type: 'number',
        min: 2,
        max: 20,
        defaultValue: 5
      },
      {
        name: 'formula',
        label: '自定义公式',
        type: 'text',
        placeholder: '例如: col1 * col2, log(col1), col1 / col2',
        required: false
      }
    ],
    defaultParams: {
      operations: 'polynomial',
      columns: '',
      degree: 2,
      n_bins: 5,
      formula: ''
    }
  }
];

// -----------------------------
// 模型训练组件
// -----------------------------
export const modelTrainingComponents: ComponentDefinition[] = [
  {
    id: 'linear-regression',
    type: ComponentType.MODEL,
    category: ComponentCategory.MODEL_TRAINING,
    name: '线性回归',
    description: '使用线性回归模型进行回归任务',
    color: '#ff9800',
    icon: 'TrendingUp',
    inputs: [
      { id: 'train', type: DataType.DATAFRAME, label: '训练数据' }
    ],
    outputs: [
      { id: 'model', type: DataType.MODEL, label: '训练后的模型' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'fit_intercept',
        label: '拟合截距',
        type: 'boolean',
        defaultValue: true
      },
      {
        name: 'normalize',
        label: '归一化',
        type: 'boolean',
        defaultValue: false
      },
      {
        name: 'max_iter',
        label: '最大迭代次数',
        type: 'number',
        min: 100,
        max: 10000,
        defaultValue: 1000
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      fit_intercept: true,
      normalize: false,
      max_iter: 1000
    }
  },
  {
    id: 'logistic-regression',
    type: ComponentType.MODEL,
    category: ComponentCategory.MODEL_TRAINING,
    name: '逻辑回归',
    description: '使用逻辑回归模型进行分类任务',
    color: '#ff9800',
    icon: 'GitBranch',
    inputs: [
      { id: 'train', type: DataType.DATAFRAME, label: '训练数据' }
    ],
    outputs: [
      { id: 'model', type: DataType.MODEL, label: '训练后的模型' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'solver',
        label: '优化算法',
        type: 'select',
        options: [
          { value: 'lbfgs', label: 'L-BFGS' },
          { value: 'newton-cg', label: 'Newton-CG' },
          { value: 'liblinear', label: 'Liblinear' },
          { value: 'sag', label: 'SAG' },
          { value: 'saga', label: 'SAGA' }
        ],
        defaultValue: 'lbfgs'
      },
      {
        name: 'penalty',
        label: '正则化',
        type: 'select',
        options: [
          { value: 'l1', label: 'L1正则' },
          { value: 'l2', label: 'L2正则' },
          { value: 'elasticnet', label: '弹性网络' },
          { value: 'none', label: '无正则化' }
        ],
        defaultValue: 'l2'
      },
      {
        name: 'C',
        label: '正则化强度',
        type: 'number',
        min: 0.001,
        max: 1000,
        step: 0.1,
        defaultValue: 1.0
      },
      {
        name: 'max_iter',
        label: '最大迭代次数',
        type: 'number',
        min: 100,
        max: 10000,
        defaultValue: 1000
      },
      {
        name: 'multi_class',
        label: '多分类方法',
        type: 'select',
        options: [
          { value: 'auto', label: '自动' },
          { value: 'ovr', label: '一对剩余' },
          { value: 'multinomial', label: '多项式' }
        ],
        defaultValue: 'auto'
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      solver: 'lbfgs',
      penalty: 'l2',
      C: 1.0,
      max_iter: 1000,
      multi_class: 'auto'
    }
  },
  {
    id: 'decision-tree',
    type: ComponentType.MODEL,
    category: ComponentCategory.MODEL_TRAINING,
    name: '决策树',
    description: '使用决策树模型进行分类或回归任务',
    color: '#ff9800',
    icon: 'GitMerge',
    inputs: [
      { id: 'train', type: DataType.DATAFRAME, label: '训练数据' }
    ],
    outputs: [
      { id: 'model', type: DataType.MODEL, label: '训练后的模型' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'task_type',
        label: '任务类型',
        type: 'select',
        options: [
          { value: 'classification', label: '分类' },
          { value: 'regression', label: '回归' }
        ],
        defaultValue: 'classification'
      },
      {
        name: 'criterion',
        label: '切分标准',
        type: 'select',
        options: [
          { value: 'gini', label: 'Gini不纯度(分类)' },
          { value: 'entropy', label: '信息熵(分类)' },
          { value: 'squared_error', label: '均方误差(回归)' },
          { value: 'absolute_error', label: '绝对误差(回归)' }
        ],
        defaultValue: 'gini'
      },
      {
        name: 'max_depth',
        label: '最大深度',
        type: 'number',
        min: 1,
        max: 100,
        defaultValue: 10
      },
      {
        name: 'min_samples_split',
        label: '最小分裂样本数',
        type: 'number',
        min: 2,
        max: 100,
        defaultValue: 2
      },
      {
        name: 'min_samples_leaf',
        label: '最小叶节点样本数',
        type: 'number',
        min: 1,
        max: 100,
        defaultValue: 1
      },
      {
        name: 'random_state',
        label: '随机种子',
        type: 'number',
        defaultValue: 42
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      task_type: 'classification',
      criterion: 'gini',
      max_depth: 10,
      min_samples_split: 2,
      min_samples_leaf: 1,
      random_state: 42
    }
  },
  {
    id: 'random-forest',
    type: ComponentType.MODEL,
    category: ComponentCategory.MODEL_TRAINING,
    name: '随机森林',
    description: '使用随机森林模型进行分类或回归任务',
    color: '#ff9800',
    icon: 'Network',
    inputs: [
      { id: 'train', type: DataType.DATAFRAME, label: '训练数据' }
    ],
    outputs: [
      { id: 'model', type: DataType.MODEL, label: '训练后的模型' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'task_type',
        label: '任务类型',
        type: 'select',
        options: [
          { value: 'classification', label: '分类' },
          { value: 'regression', label: '回归' }
        ],
        defaultValue: 'classification'
      },
      {
        name: 'n_estimators',
        label: '树的数量',
        type: 'number',
        min: 10,
        max: 1000,
        defaultValue: 100
      },
      {
        name: 'criterion',
        label: '切分标准',
        type: 'select',
        options: [
          { value: 'gini', label: 'Gini不纯度(分类)' },
          { value: 'entropy', label: '信息熵(分类)' },
          { value: 'squared_error', label: '均方误差(回归)' },
          { value: 'absolute_error', label: '绝对误差(回归)' }
        ],
        defaultValue: 'gini'
      },
      {
        name: 'max_depth',
        label: '最大深度',
        type: 'number',
        min: 1,
        max: 100,
        defaultValue: 10
      },
      {
        name: 'max_features',
        label: '最大特征数',
        type: 'select',
        options: [
          { value: 'sqrt', label: '平方根' },
          { value: 'log2', label: '对数' },
          { value: 'auto', label: '自动' }
        ],
        defaultValue: 'sqrt'
      },
      {
        name: 'bootstrap',
        label: '自助采样',
        type: 'boolean',
        defaultValue: true
      },
      {
        name: 'random_state',
        label: '随机种子',
        type: 'number',
        defaultValue: 42
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      task_type: 'classification',
      n_estimators: 100,
      criterion: 'gini',
      max_depth: 10,
      max_features: 'sqrt',
      bootstrap: true,
      random_state: 42
    }
  },
  {
    id: 'svm',
    type: ComponentType.MODEL,
    category: ComponentCategory.MODEL_TRAINING,
    name: '支持向量机',
    description: '使用支持向量机进行分类或回归任务',
    color: '#ff9800',
    icon: 'Box',
    inputs: [
      { id: 'train', type: DataType.DATAFRAME, label: '训练数据' }
    ],
    outputs: [
      { id: 'model', type: DataType.MODEL, label: '训练后的模型' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'task_type',
        label: '任务类型',
        type: 'select',
        options: [
          { value: 'classification', label: '分类' },
          { value: 'regression', label: '回归' }
        ],
        defaultValue: 'classification'
      },
      {
        name: 'kernel',
        label: '核函数',
        type: 'select',
        options: [
          { value: 'linear', label: '线性' },
          { value: 'poly', label: '多项式' },
          { value: 'rbf', label: '径向基函数(RBF)' },
          { value: 'sigmoid', label: 'Sigmoid' }
        ],
        defaultValue: 'rbf'
      },
      {
        name: 'C',
        label: '正则化参数',
        type: 'number',
        min: 0.001,
        max: 1000,
        step: 0.1,
        defaultValue: 1.0
      },
      {
        name: 'gamma',
        label: 'Gamma',
        type: 'select',
        options: [
          { value: 'scale', label: '缩放' },
          { value: 'auto', label: '自动' }
        ],
        defaultValue: 'scale'
      },
      {
        name: 'degree',
        label: '多项式次数',
        type: 'number',
        min: 1,
        max: 10,
        defaultValue: 3
      },
      {
        name: 'probability',
        label: '概率估计',
        type: 'boolean',
        defaultValue: true
      },
      {
        name: 'random_state',
        label: '随机种子',
        type: 'number',
        defaultValue: 42
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      task_type: 'classification',
      kernel: 'rbf',
      C: 1.0,
      gamma: 'scale',
      degree: 3,
      probability: true,
      random_state: 42
    }
  },
  {
    id: 'gradient-boosting',
    type: ComponentType.MODEL,
    category: ComponentCategory.MODEL_TRAINING,
    name: '梯度提升树',
    description: '使用梯度提升树进行分类或回归任务',
    color: '#ff9800',
    icon: 'TrendingUp',
    inputs: [
      { id: 'train', type: DataType.DATAFRAME, label: '训练数据' }
    ],
    outputs: [
      { id: 'model', type: DataType.MODEL, label: '训练后的模型' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'task_type',
        label: '任务类型',
        type: 'select',
        options: [
          { value: 'classification', label: '分类' },
          { value: 'regression', label: '回归' }
        ],
        defaultValue: 'classification'
      },
      {
        name: 'n_estimators',
        label: '树的数量',
        type: 'number',
        min: 10,
        max: 1000,
        defaultValue: 100
      },
      {
        name: 'learning_rate',
        label: '学习率',
        type: 'number',
        min: 0.001,
        max: 1,
        step: 0.001,
        defaultValue: 0.1
      },
      {
        name: 'max_depth',
        label: '最大深度',
        type: 'number',
        min: 1,
        max: 100,
        defaultValue: 3
      },
      {
        name: 'subsample',
        label: '子样本比例',
        type: 'number',
        min: 0.1,
        max: 1,
        step: 0.1,
        defaultValue: 1.0
      },
      {
        name: 'random_state',
        label: '随机种子',
        type: 'number',
        defaultValue: 42
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      task_type: 'classification',
      n_estimators: 100,
      learning_rate: 0.1,
      max_depth: 3,
      subsample: 1.0,
      random_state: 42
    }
  },
  {
    id: 'kmeans',
    type: ComponentType.MODEL,
    category: ComponentCategory.MODEL_TRAINING,
    name: 'K均值聚类',
    description: '使用K均值算法进行聚类分析',
    color: '#ff9800',
    icon: 'CircleDot',
    inputs: [
      { id: 'train', type: DataType.DATAFRAME, label: '训练数据' }
    ],
    outputs: [
      { id: 'model', type: DataType.MODEL, label: '训练后的模型' },
      { id: 'data', type: DataType.DATAFRAME, label: '带聚类标签的数据' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'n_clusters',
        label: '聚类数',
        type: 'number',
        min: 2,
        max: 100,
        defaultValue: 5
      },
      {
        name: 'init',
        label: '初始化方法',
        type: 'select',
        options: [
          { value: 'k-means++', label: 'K-Means++' },
          { value: 'random', label: '随机' }
        ],
        defaultValue: 'k-means++'
      },
      {
        name: 'n_init',
        label: '初始化运行次数',
        type: 'number',
        min: 1,
        max: 50,
        defaultValue: 10
      },
      {
        name: 'max_iter',
        label: '最大迭代次数',
        type: 'number',
        min: 10,
        max: 1000,
        defaultValue: 300
      },
      {
        name: 'random_state',
        label: '随机种子',
        type: 'number',
        defaultValue: 42
      }
    ],
    defaultParams: {
      features: '',
      n_clusters: 5,
      init: 'k-means++',
      n_init: 10,
      max_iter: 300,
      random_state: 42
    }
  }
];

// -----------------------------
// 模型评估组件
// -----------------------------
export const modelEvaluationComponents: ComponentDefinition[] = [
  {
    id: 'classification-metrics',
    type: ComponentType.EVALUATION,
    category: ComponentCategory.EVALUATION,
    name: '分类评估指标',
    description: '计算分类模型的各种评估指标',
    color: '#9c27b0',
    icon: 'BarChart2',
    inputs: [
      { id: 'model', type: DataType.MODEL, label: '模型' },
      { id: 'test', type: DataType.DATAFRAME, label: '测试数据' }
    ],
    outputs: [
      { id: 'metrics', type: DataType.OBJECT, label: '评估指标' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'metrics',
        label: '评估指标',
        type: 'select',
        options: [
          { value: 'accuracy', label: '准确率' },
          { value: 'precision', label: '精确率' },
          { value: 'recall', label: '召回率' },
          { value: 'f1', label: 'F1分数' },
          { value: 'auc', label: 'AUC' },
          { value: 'all', label: '所有指标' }
        ],
        defaultValue: 'all'
      },
      {
        name: 'average',
        label: '多分类平均方式',
        type: 'select',
        options: [
          { value: 'micro', label: '微平均' },
          { value: 'macro', label: '宏平均' },
          { value: 'weighted', label: '加权平均' }
        ],
        defaultValue: 'weighted'
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      metrics: 'all',
      average: 'weighted'
    }
  },
  {
    id: 'regression-metrics',
    type: ComponentType.EVALUATION,
    category: ComponentCategory.EVALUATION,
    name: '回归评估指标',
    description: '计算回归模型的各种评估指标',
    color: '#9c27b0',
    icon: 'TrendingUp',
    inputs: [
      { id: 'model', type: DataType.MODEL, label: '模型' },
      { id: 'test', type: DataType.DATAFRAME, label: '测试数据' }
    ],
    outputs: [
      { id: 'metrics', type: DataType.OBJECT, label: '评估指标' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'metrics',
        label: '评估指标',
        type: 'select',
        options: [
          { value: 'mse', label: '均方误差(MSE)' },
          { value: 'rmse', label: '均方根误差(RMSE)' },
          { value: 'mae', label: '平均绝对误差(MAE)' },
          { value: 'r2', label: '决定系数(R²)' },
          { value: 'all', label: '所有指标' }
        ],
        defaultValue: 'all'
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      metrics: 'all'
    }
  },
  {
    id: 'confusion-matrix',
    type: ComponentType.EVALUATION,
    category: ComponentCategory.EVALUATION,
    name: '混淆矩阵',
    description: '生成分类模型的混淆矩阵',
    color: '#9c27b0',
    icon: 'Grid',
    inputs: [
      { id: 'model', type: DataType.MODEL, label: '模型' },
      { id: 'test', type: DataType.DATAFRAME, label: '测试数据' }
    ],
    outputs: [
      { id: 'matrix', type: DataType.OBJECT, label: '混淆矩阵' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'normalize',
        label: '归一化',
        type: 'boolean',
        defaultValue: false
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      normalize: false
    }
  },
  {
    id: 'roc-curve',
    type: ComponentType.EVALUATION,
    category: ComponentCategory.EVALUATION,
    name: 'ROC曲线',
    description: '生成ROC曲线和AUC值',
    color: '#9c27b0',
    icon: 'Activity',
    inputs: [
      { id: 'model', type: DataType.MODEL, label: '模型' },
      { id: 'test', type: DataType.DATAFRAME, label: '测试数据' }
    ],
    outputs: [
      { id: 'roc_data', type: DataType.OBJECT, label: 'ROC数据' },
      { id: 'auc', type: DataType.NUMBER, label: 'AUC值' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'pos_label',
        label: '正例标签',
        type: 'string',
        placeholder: '留空使用最后一个类别',
        required: false
      },
      {
        name: 'multi_class',
        label: '多分类策略',
        type: 'select',
        options: [
          { value: 'ovr', label: '一对剩余(OvR)' },
          { value: 'ovo', label: '一对一(OvO)' }
        ],
        defaultValue: 'ovr'
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      pos_label: '',
      multi_class: 'ovr'
    }
  },
  {
    id: 'learning-curve',
    type: ComponentType.EVALUATION,
    category: ComponentCategory.EVALUATION,
    name: '学习曲线',
    description: '生成学习曲线以评估模型的过拟合或欠拟合',
    color: '#9c27b0',
    icon: 'TrendingUp',
    inputs: [
      { id: 'model', type: DataType.MODEL, label: '模型' },
      { id: 'data', type: DataType.DATAFRAME, label: '数据集' }
    ],
    outputs: [
      { id: 'curve_data', type: DataType.OBJECT, label: '曲线数据' }
    ],
    params: [
      {
        name: 'features',
        label: '特征列',
        type: 'string',
        placeholder: '列名，用逗号分隔',
        required: true
      },
      {
        name: 'target',
        label: '目标列',
        type: 'string',
        placeholder: '目标变量列名',
        required: true
      },
      {
        name: 'cv',
        label: '交叉验证折数',
        type: 'number',
        min: 2,
        max: 20,
        defaultValue: 5
      },
      {
        name: 'scoring',
        label: '评分方式',
        type: 'select',
        options: [
          { value: 'accuracy', label: '准确率(分类)' },
          { value: 'f1', label: 'F1分数(分类)' },
          { value: 'precision', label: '精确率(分类)' },
          { value: 'recall', label: '召回率(分类)' },
          { value: 'r2', label: 'R²(回归)' },
          { value: 'neg_mean_squared_error', label: '负均方误差(回归)' }
        ],
        defaultValue: 'accuracy'
      },
      {
        name: 'n_jobs',
        label: '并行作业数',
        type: 'number',
        min: -1,
        max: 12,
        defaultValue: -1
      }
    ],
    defaultParams: {
      features: '',
      target: '',
      cv: 5,
      scoring: 'accuracy',
      n_jobs: -1
    }
  }
];

// -----------------------------
// 可视化组件
// -----------------------------
export const visualizationComponents: ComponentDefinition[] = [
  {
    id: 'bar-chart',
    type: ComponentType.VISUALIZATION,
    category: ComponentCategory.VISUALIZATION,
    name: '柱状图',
    description: '创建柱状图或条形图',
    color: '#e91e63',
    icon: 'BarChart',
    inputs: [
      { id: 'data', type: DataType.DATAFRAME, label: '数据集' }
    ],
    outputs: [
      { id: 'chart', type: DataType.IMAGE, label: '图表' }
    ],
    params: [
      {
        name: 'x_column',
        label: 'X轴列',
        type: 'string',
        placeholder: '列名',
        required: true
      },
      {
        name: 'y_column',
        label: 'Y轴列',
        type: 'string',
        placeholder: '列名',
        required: true
      },
      {
        name: 'title',
        label: '标题',
        type: 'string',
        placeholder: '图表标题',
        defaultValue: '柱状图'
      },
      {
        name: 'xlabel',
        label: 'X轴标签',
        type: 'string',
        placeholder: 'X轴标签',
        defaultValue: ''
      },
      {
        name: 'ylabel',
        label: 'Y轴标签',
        type: 'string',
        placeholder: 'Y轴标签',
        defaultValue: ''
      },
      {
        name: 'color',
        label: '颜色',
        type: 'color',
        defaultValue: '#4caf50'
      },
      {
        name: 'orientation',
        label: '方向',
        type: 'select',
        options: [
          { value: 'vertical', label: '垂直' },
          { value: 'horizontal', label: '水平' }
        ],
        defaultValue: 'vertical'
      }
    ],
    defaultParams: {
      x_column: '',
      y_column: '',
      title: '柱状图',
      xlabel: '',
      ylabel: '',
      color: '#4caf50',
      orientation: 'vertical'
    }
  },
  {
    id: 'line-chart',
    type: ComponentType.VISUALIZATION,
    category: ComponentCategory.VISUALIZATION,
    name: '折线图',
    description: '创建折线图或曲线图',
    color: '#e91e63',
    icon: 'LineChart',
    inputs: [
      { id: 'data', type: DataType.DATAFRAME, label: '数据集' }
    ],
    outputs: [
      { id: 'chart', type: DataType.IMAGE, label: '图表' }
    ],
    params: [
      {
        name: 'x_column',
        label: 'X轴列',
        type: 'string',
        placeholder: '列名',
        required: true
      },
      {
        name: 'y_column',
        label: 'Y轴列',
        type: 'string',
        placeholder: '列名，多列用逗号分隔',
        required: true
      },
      {
        name: 'title',
        label: '标题',
        type: 'string',
        placeholder: '图表标题',
        defaultValue: '折线图'
      },
      {
        name: 'xlabel',
        label: 'X轴标签',
        type: 'string',
        placeholder: 'X轴标签',
        defaultValue: ''
      },
      {
        name: 'ylabel',
        label: 'Y轴标签',
        type: 'string',
        placeholder: 'Y轴标签',
        defaultValue: ''
      },
      {
        name: 'color',
        label: '颜色',
        type: 'color',
        defaultValue: '#1976d2'
      },
      {
        name: 'markers',
        label: '显示标记',
        type: 'boolean',
        defaultValue: true
      },
      {
        name: 'line_style',
        label: '线条样式',
        type: 'select',
        options: [
          { value: 'solid', label: '实线' },
          { value: 'dashed', label: '虚线' },
          { value: 'dotted', label: '点线' }
        ],
        defaultValue: 'solid'
      }
    ],
    defaultParams: {
      x_column: '',
      y_column: '',
      title: '折线图',
      xlabel: '',
      ylabel: '',
      color: '#1976d2',
      markers: true,
      line_style: 'solid'
    }
  },
  {
    id: 'scatter-plot',
    type: ComponentType.VISUALIZATION,
    category: ComponentCategory.VISUALIZATION,
    name: '散点图',
    description: '创建散点图或气泡图',
    color: '#e91e63',
    icon: 'CircleDot',
    inputs: [
      { id: 'data', type: DataType.DATAFRAME, label: '数据集' }
    ],
    outputs: [
      { id: 'chart', type: DataType.IMAGE, label: '图表' }
    ],
    params: [
      {
        name: 'x_column',
        label: 'X轴列',
        type: 'string',
        placeholder: '列名',
        required: true
      },
      {
        name: 'y_column',
        label: 'Y轴列',
        type: 'string',
        placeholder: '列名',
        required: true
      },
      {
        name: 'color_column',
        label: '颜色列',
        type: 'string',
        placeholder: '分类列名',
        required: false
      },
      {
        name: 'size_column',
        label: '大小列',
        type: 'string',
        placeholder: '数值列名',
        required: false
      },
      {
        name: 'title',
        label: '标题',
        type: 'string',
        placeholder: '图表标题',
        defaultValue: '散点图'
      },
      {
        name: 'xlabel',
        label: 'X轴标签',
        type: 'string',
        placeholder: 'X轴标签',
        defaultValue: ''
      },
      {
        name: 'ylabel',
        label: 'Y轴标签',
        type: 'string',
        placeholder: 'Y轴标签',
        defaultValue: ''
      },
      {
        name: 'alpha',
        label: '透明度',
        type: 'number',
        min: 0.1,
        max: 1,
        step: 0.1,
        defaultValue: 0.8
      }
    ],
    defaultParams: {
      x_column: '',
      y_column: '',
      color_column: '',
      size_column: '',
      title: '散点图',
      xlabel: '',
      ylabel: '',
      alpha: 0.8
    }
  },
  {
    id: 'histogram',
    type: ComponentType.VISUALIZATION,
    category: ComponentCategory.VISUALIZATION,
    name: '直方图',
    description: '创建数据分布的直方图',
    color: '#e91e63',
    icon: 'BarChart2',
    inputs: [
      { id: 'data', type: DataType.DATAFRAME, label: '数据集' }
    ],
    outputs: [
      { id: 'chart', type: DataType.IMAGE, label: '图表' }
    ],
    params: [
      {
        name: 'column',
        label: '数据列',
        type: 'string',
        placeholder: '列名',
        required: true
      },
      {
        name: 'bins',
        label: '直方图分箱数',
        type: 'number',
        min: 5,
        max: 100,
        defaultValue: 20
      },
      {
        name: 'title',
        label: '标题',
        type: 'string',
        placeholder: '图表标题',
        defaultValue: '直方图'
      },
      {
        name: 'xlabel',
        label: 'X轴标签',
        type: 'string',
        placeholder: 'X轴标签',
        defaultValue: ''
      },
      {
        name: 'ylabel',
        label: 'Y轴标签',
        type: 'string',
        placeholder: 'Y轴标签',
        defaultValue: '频率'
      },
      {
        name: 'color',
        label: '颜色',
        type: 'color',
        defaultValue: '#9c27b0'
      },
      {
        name: 'kde',
        label: '显示核密度估计',
        type: 'boolean',
        defaultValue: false
      }
    ],
    defaultParams: {
      column: '',
      bins: 20,
      title: '直方图',
      xlabel: '',
      ylabel: '频率',
      color: '#9c27b0',
      kde: false
    }
  },
  {
    id: 'heatmap',
    type: ComponentType.VISUALIZATION,
    category: ComponentCategory.VISUALIZATION,
    name: '热力图',
    description: '创建相关性或数据矩阵的热力图',
    color: '#e91e63',
    icon: 'Grid',
    inputs: [
      { id: 'data', type: DataType.DATAFRAME, label: '数据集' }
    ],
    outputs: [
      { id: 'chart', type: DataType.IMAGE, label: '图表' }
    ],
    params: [
      {
        name: 'columns',
        label: '选择列',
        type: 'string',
        placeholder: '列名，用逗号分隔，留空使用所有数值列',
        required: false
      },
      {
        name: 'computation',
        label: '计算方式',
        type: 'select',
        options: [
          { value: 'correlation', label: '相关性矩阵' },
          { value: 'covariance', label: '协方差矩阵' },
          { value: 'raw', label: '原始数据' }
        ],
        defaultValue: 'correlation'
      },
      {
        name: 'title',
        label: '标题',
        type: 'string',
        placeholder: '图表标题',
        defaultValue: '热力图'
      },
      {
        name: 'cmap',
        label: '颜色映射',
        type: 'select',
        options: [
          { value: 'viridis', label: 'Viridis' },
          { value: 'plasma', label: 'Plasma' },
          { value: 'inferno', label: 'Inferno' },
          { value: 'magma', label: 'Magma' },
          { value: 'cividis', label: 'Cividis' },
          { value: 'coolwarm', label: 'Coolwarm' },
          { value: 'RdBu', label: 'Red-Blue' }
        ],
        defaultValue: 'coolwarm'
      },
      {
        name: 'show_values',
        label: '显示数值',
        type: 'boolean',
        defaultValue: true
      },
      {
        name: 'cluster',
        label: '聚类排序',
        type: 'boolean',
        defaultValue: false
      }
    ],
    defaultParams: {
      columns: '',
      computation: 'correlation',
      title: '热力图',
      cmap: 'coolwarm',
      show_values: true,
      cluster: false
    }
  },
  {
    id: 'pie-chart',
    type: ComponentType.VISUALIZATION,
    category: ComponentCategory.VISUALIZATION,
    name: '饼图',
    description: '创建饼图或环形图',
    color: '#e91e63',
    icon: 'PieChart',
    inputs: [
      { id: 'data', type: DataType.DATAFRAME, label: '数据集' }
    ],
    outputs: [
      { id: 'chart', type: DataType.IMAGE, label: '图表' }
    ],
    params: [
      {
        name: 'labels_column',
        label: '标签列',
        type: 'string',
        placeholder: '标签列名',
        required: true
      },
      {
        name: 'values_column',
        label: '数值列',
        type: 'string',
        placeholder: '数值列名',
        required: true
      },
      {
        name: 'title',
        label: '标题',
        type: 'string',
        placeholder: '图表标题',
        defaultValue: '饼图'
      },
      {
        name: 'donut',
        label: '环形图',
        type: 'boolean',
        defaultValue: false
      },
      {
        name: 'show_pct',
        label: '显示百分比',
        type: 'boolean',
        defaultValue: true
      },
      {
        name: 'start_angle',
        label: '起始角度',
        type: 'number',
        min: 0,
        max: 360,
        defaultValue: 0
      }
    ],
    defaultParams: {
      labels_column: '',
      values_column: '',
      title: '饼图',
      donut: false,
      show_pct: true,
      start_angle: 0
    }
  }
];

// -----------------------------
// 导出组件
// -----------------------------

// 合并所有组件
export const allComponents: ComponentDefinition[] = [
  ...dataInputComponents,
  ...dataProcessingComponents,
  ...modelTrainingComponents,
  ...modelEvaluationComponents,
  ...visualizationComponents
];

// 修复分类评估指标中的lint错误 - 移除multiple属性
const fixedComponents = allComponents.map(component => {
  if (component.id === 'classification-metrics' || component.id === 'regression-metrics') {
    return {
      ...component,
      params: component.params.map(param => {
        if (param.name === 'metrics') {
          // 删除multiple属性
          const { multiple, ...rest } = param as any;
          return rest;
        }
        return param;
      })
    };
  }
  return component;
});

// 导出默认组件
export default fixedComponents;
