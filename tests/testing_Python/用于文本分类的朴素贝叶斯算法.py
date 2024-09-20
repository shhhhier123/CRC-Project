from sklearn.metrics import classification_report, accuracy_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from collections import Counter
from tqdm import tqdm
import pandas as pd
import numpy as np
import time

tqdm.pandas()

"""
可灵活调整不同特征构造方法，输出特征为 (n_samples, n_features)，
可以是 scipy.sparse.csr_matrix 或 numpy.array, 特征选择后 n_features 可自定
"""


class FeatureExtractor:
    """
    特征处理，包括特征提取和特征选择
    """

    def extract_tfidf_fit(self, train_data):
        """
        由训练集构建词表、idf
        """
        self.extractor = TfidfVectorizer()
        self.extractor.fit(train_data)

    def extract_tfidf_tranform(self, data):
        """
        根据词表计算 tf-idf
        """
        return self.extractor.transform(data)

    def encode_label(self, labels):
        """
        将文本标签编码为数字
        """
        self.le = LabelEncoder()
        self.le.fit(labels)
        self.label_dict = dict(zip(self.le.classes_, range(len(self.le.classes_))))

    def labels_to_ids(self, labels):
        return self.le.transform(labels)


class NBModel:
    def __init__(self, alpha=1) -> None:
        """
        实现用于文本分类的朴素贝叶斯算法

        Args:
            alpha (int, optional): 拉普拉斯平滑参数. Defaults to 1.
        """
        # 分类类别数
        self.label_siz = 0

        # 先验概率（不采用）
        # self.prior_prob = np.zeros(1)

        # 似然概率
        self.like_prob = np.zeros(1)

        # 拉普拉斯平滑参数（不采用）
        # 对于某一个词项的频率为0的情况，因为采用加法来考虑其在不同类别上的权值，
        # 因此不考虑会导致整个value归零的情况；而且基数采用的是tf-idf值，因此不做拉普拉斯平滑

        # self.alpha = alpha

    def fit(self, x, y):
        """
        根据训练集训练朴素贝叶斯模型，计算标签先验分布以及特征条件分布

        Args:
            x (scipy.sparse.csr_matrix | numpy.array): 训练集输入 (n_samples, n_features)
            y (numpy.array): 训练集标签 (n_samples,)
        """
        start_time = time.time()
        # 测试区
        # min_val = np.min(x)
        # max_val = np.max(x)

        # 记录样本数
        self.label_siz = max(y) - min(y) + 1

        # 先验概率：类别为y的样本数 / 总样本数
        # &采用先验概率的验证结果：acc=0.6279 of 3768 entries
        # &不采用先验概率的验证结果：acc=0.6484 of 3768 entries
        # 考虑为在该数据集上，先验分布不显著导致的

        # self.prior_prob = np.zeros([self.label_siz, ])
        # prior_count = Counter(y)
        # for k, v in prior_count.items():
        #     self.prior_prob[k] = v
        # self.prior_prob /= np.sum(self.prior_prob)

        # 似然概率：类别为y的样本中x_i出现次数 / 类别为y的样本中总词数（该项）
        self.like_prob = np.zeros((self.label_siz, x.shape[1]))
        for i, entry in enumerate(x):
            for j in range(len(entry.data)):
                
                # @self.like_prob.shape = [10, 61900]
                # @y.shape = [33916, ]
                # @entry.indices.shape = [30, ]
                # @entry.data.shape = [30, ]
                
                self.like_prob[y[i], entry.indices[j]] += entry.data[j]

        # 在词项方向上做均一化
        for i in range(x.shape[1]):
            total_len = sum(self.like_prob[:, i])
            if total_len != 0:
                self.like_prob[:, i] /= total_len

        print(f"训练时间：{time.time() - start_time} s")

    def predict(self, x):
        """
        预测测试集标签，计算后验概率

        Args:
            x (scipy.sparse.csr_matrix | numpy.array): 测试集输入  (n_samples, n_features)
        Return:
            pred (numpy.array): 测试集预测标签 (n_samples,)
        """
        # 将数据集由csr_matrix转化为numpy数组处理
        x = x.toarray()

        # pred (numpy.array): 测试集预测标签 (n_samples,)
        pred = np.zeros((x.shape[0],), dtype=int)

        # pred在10个类别上的分布
        pred_dist = np.zeros((x.shape[0], self.label_siz))

        for i in range(x.shape[0]):

            # @pred_dist[i, ].shape = [10, ]
            # @tar_x.shape = [10, 61900]
            # @self.like_prob.shape = [10, 61900]

            tar_x = np.repeat(x[i, ][np.newaxis, :], 10, axis=0)
            pred_dist[i, ] = np.sum(tar_x * self.like_prob, axis=1)

            # 不采用先验概率的情况
            # pred_dist[i, ] *= self.prior_prob

        # 取最大概率类别输出
        for i in range(x.shape[0]):
            pred[i] = np.argmax(pred_dist[i, ])
        return pred

    def report(self, labels, preds, target_names=None):
        """
        评测模型结果

        Args:
            labels (numpy.array): 测试集真实标签
            preds (numpy.array): 测试集预测标签
            label_names (List[str], optional): 标签名称. Defaults to None.
        """
        print(classification_report(labels, preds, target_names=target_names, digits=4))


if __name__ == '__main__':
    feature_extractor = FeatureExtractor()

    # 加载处理好的数据
    train_data = pd.read_json("data/seg_train.json", lines=True)
    eval_data = pd.read_json("data/seg_eval.json", lines=True)
    test_data = pd.read_json("data/seg_test.json", lines=True)

    train_seg_data = train_data["content"]
    eval_seg_data = eval_data["content"]
    test_seg_data = test_data["content"]

    train_data.head()

    train_count = Counter(train_data["label"])
    print("训练集标签分布：", train_count)
    eval_count = Counter(eval_data["label"])
    print("验证集标签分布：", eval_count)

    # 编码标签
    feature_extractor.encode_label(train_data["label"])
    train_label_ids = feature_extractor.labels_to_ids(train_data["label"])
    eval_label_ids = feature_extractor.labels_to_ids(eval_data["label"])
    # train_label_ids

    # 提取文本特征
    feature_extractor.extract_tfidf_fit(train_seg_data)
    train_features = feature_extractor.extract_tfidf_tranform(train_seg_data)
    eval_features = feature_extractor.extract_tfidf_tranform(eval_seg_data)
    test_features = feature_extractor.extract_tfidf_tranform(test_seg_data)

    print(train_features.get_shape())   # 33916是训练集样本数量，61900是词表大小，可以进一步特征选择
    print(train_features)   # 稀疏矩阵形式打印效果

    # scipy.sparse.csr_matrix 转 numpy.array（未使用）
    # train_features = train_features.toarray()
    # eval_features = eval_features.toarray()
    # test_features = test_features.toarray()

    model = NBModel()
    # 训练
    model.fit(train_features, train_label_ids)
    # 评测验证集结果
    eval_preds = model.predict(eval_features)
    print(model.report(eval_label_ids, eval_preds, target_names=feature_extractor.le.classes_))

    # 保存测试集结果
"""
    test_preds = model.predict(test_features).tolist()
    no = "__"
    name = "__"
    with open(f"{no}-{name}.txt", "w") as f:
        for p in test_preds:
            f.write(feature_extractor.le.classes_[p] + "\n")
"""
