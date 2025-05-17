# 导入所需库
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_curve, auc
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from collections import Counter
from wordcloud import WordCloud
import matplotlib as mpl
from IPython.display import display, Markdown

# 设置绘图参数
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']  # 使用环境中可用的字体
plt.rcParams['axes.unicode_minus'] = False  # 确保负号正确显示
mpl.rcParams['figure.figsize'] = (12, 8)  # 设置图形大小
plt.style.use('seaborn-v0_8-whitegrid')  # 设置风格

# 英文标签映射（用于可视化）
labels_en = {
    '情感标签': 'Sentiment',
    '数量': 'Count',
    '积极': 'Positive',
    '消极': 'Negative',
    '评论长度（词数）': 'Review Length (Words)',
    '评论数量': 'Number of Reviews',
    '平均长度': 'Mean Length',
    '中位长度': 'Median Length',
    '不同情感类别的评论长度分布': 'Review Length Distribution by Sentiment',
    '所有评论中最常见的20个词': 'Top 20 Words in All Reviews',
    '词频': 'Word Frequency',
    '词汇': 'Words',
    '积极评论中最常见的20个词': 'Top 20 Words in Positive Reviews',
    '消极评论中最常见的20个词': 'Top 20 Words in Negative Reviews',
    'IMDB电影评论词云': 'IMDB Movie Review Word Cloud',
    '积极评论词云': 'Positive Reviews Word Cloud',
    '消极评论词云': 'Negative Reviews Word Cloud',
    '预测标签': 'Predicted Label',
    '真实标签': 'True Label',
    '混淆矩阵': 'Confusion Matrix',
    '假正例率': 'False Positive Rate',
    '真正例率': 'True Positive Rate',
    'ROC曲线': 'ROC Curve',
    '不同模型的准确率比较': 'Accuracy Comparison of Different Models',
    '模型': 'Model',
    '准确率': 'Accuracy',
    '最具指示积极情感的15个词汇': 'Top 15 Words Indicating Positive Sentiment',
    '最具指示消极情感的15个词汇': 'Top 15 Words Indicating Negative Sentiment',
    '系数值': 'Coefficient Value',
    '特征': 'Feature',
    '重要性': 'Importance',
    '预测结果可视化': 'Prediction Results Visualization',
    '样本': 'Sample'
}

# 下载必要的NLTK资源
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('punkt')

# 1. 数据加载与探索
# 加载IMDB数据集
df = pd.read_csv('imdb_dataset.csv')

# 显示数据基本信息
display(Markdown("## 数据集基本信息"))
print(f"数据集形状: {df.shape}")
print(f"数据集列名: {df.columns.tolist()}")
display(df.head())

# 检查缺失值
display(Markdown("## 缺失值检查"))
missing_values = df.isnull().sum()
print(missing_values)

# 检查标签分布
display(Markdown("## 情感标签分布"))
sentiment_counts = df['sentiment'].value_counts()
print(sentiment_counts)

# 可视化标签分布（使用英文标签）
plt.figure(figsize=(10, 6))
sns.countplot(x='sentiment', data=df, palette='viridis')
plt.title('Sentiment Distribution')
plt.xlabel('Sentiment')
plt.ylabel('Count')
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()


# 2. 数据预处理
def clean_text(text):
    """文本清洗函数"""
    if isinstance(text, str):
        # 转换为小写
        text = text.lower()
        # 移除HTML标签
        text = re.sub(r'<.*?>', '', text)
        # 只保留字母
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    return ''

# 文本清洗
df['cleaned_review'] = df['review'].apply(clean_text)

# 标签编码
label_encoder = LabelEncoder()
df['sentiment_encoded'] = label_encoder.fit_transform(df['sentiment'])

print("标签映射:", dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_))))

# 显示清洗后的文本示例
display(Markdown("## 清洗前后的文本示例"))
text_samples = pd.DataFrame({
    '原始文本': df['review'].head(),
    '清洗后文本': df['cleaned_review'].head()
})
display(text_samples)


# 3. 特征工程和数据划分
# 将数据集划分为训练集和测试集
df_train, df_test = train_test_split(
    df, 
    test_size=0.2, 
    random_state=42, 
    stratify=df['sentiment_encoded']
)

print(f"训练集大小: {df_train.shape}")
print(f"测试集大小: {df_test.shape}")

# 特征提取 - 使用TF-IDF向量化
tfidf_vectorizer = TfidfVectorizer(
    max_features=10000,
    min_df=2,
    max_df=0.8,
    stop_words='english'
)

# 在训练集上拟合并转换
X_train_tfidf = tfidf_vectorizer.fit_transform(df_train['cleaned_review'])
# 只转换测试集
X_test_tfidf = tfidf_vectorizer.transform(df_test['cleaned_review'])

# 获取标签
y_train = df_train['sentiment_encoded']
y_test = df_test['sentiment_encoded']

print(f"特征维度: {X_train_tfidf.shape[1]}")

# 查看一些TF-IDF特征的示例
feature_names = tfidf_vectorizer.get_feature_names_out()
display(Markdown("## TF-IDF特征示例"))
print(f"特征总数: {len(feature_names)}")
print(f"前20个特征: {feature_names[:20]}")


# 4. 模型训练与评估函数
def train_evaluate_model(X_train, X_test, y_train, y_test, model_name='logistic'):
    """训练并评估模型"""
    if model_name == 'logistic':
        model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    elif model_name == 'random_forest':
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_name == 'svm':
        model = LinearSVC(C=1.0, random_state=42)
    elif model_name == 'naive_bayes':
        model = MultinomialNB(alpha=1.0)
    else:
        raise ValueError(f"不支持的模型: {model_name}")
    
    # 训练模型
    model.fit(X_train, y_train)
    
    # 预测
    y_pred = model.predict(X_test)
    
    # 评估模型
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    # 显示评估结果
    display(Markdown(f"### {model_name.replace('_', ' ').title()} 模型评估"))
    print(f"准确率: {accuracy:.4f}")
    print(f"分类报告:\n{report}")
    
    # 绘制混淆矩阵（使用英文标签）
    plt.figure(figsize=(5, 4))
    sns.heatmap(
        cm, 
        annot=True, 
        fmt='d', 
        cmap='Blues', 
        xticklabels=['Negative', 'Positive'], 
        yticklabels=['Negative', 'Positive']
    )
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.title(f'Confusion Matrix - {model_name.replace("_", " ").title()}')
    plt.tight_layout()
    plt.show()
    
    # 如果模型支持predict_proba，绘制ROC曲线
    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        roc_auc = auc(fpr, tpr)
        
        plt.figure(figsize=(5, 4))
        plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC Curve (AUC = {roc_auc:.2f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title(f'ROC Curve - {model_name.replace("_", " ").title()}')
        plt.legend(loc="lower right")
        plt.tight_layout()
        plt.show()
    
    return model, accuracy, report, cm

# 5. 训练和评估逻辑回归模型
logistic_model, logistic_acc, logistic_report, logistic_cm = train_evaluate_model(
    X_train_tfidf, X_test_tfidf, y_train, y_test, model_name='logistic'
)