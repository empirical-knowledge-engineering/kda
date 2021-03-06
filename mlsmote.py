# -*- coding: utf-8 -*-
# Importing required Library
import numpy as np
import pandas as pd
import random
from sklearn.datasets import make_classification
from sklearn.neighbors import NearestNeighbors


def create_dataset(n_sample=1000):
    '''
    Create a unevenly distributed sample data set multilabel
    classification using make_classification function

    args
    nsample: int, Number of sample to be created

    return
    X: pandas.DataFrame, feature vector dataframe with 10 features
    y: pandas.DataFrame, target vector dataframe with 5 labels
    '''
    X, y = make_classification(n_classes=5, class_sep=2,
                               weights=[0.1, 0.025, 0.205, 0.008, 0.9], n_informative=3, n_redundant=1, flip_y=0,
                               n_features=10, n_clusters_per_class=1, n_samples=1000, random_state=10)
    y = pd.get_dummies(y, prefix='class')
    return pd.DataFrame(X), y


def get_irlb(df):
    columns = df.columns
    n = len(columns)
    irpl = np.zeros(n)
    for column in range(n):
        vc = df[columns[column]].value_counts()
        if 1 in vc:
            irpl[column] = vc[1]
        else:
            irpl[column] = 0
    irpl = max(irpl) / [i if i > 0 else 1 for i in irpl]
    mir = np.average(irpl)
    return irpl, mir


def get_tail_label(df):
    """
    Give tail label colums of the given target dataframe

    args
    df: pandas.DataFrame, target label df whose tail label has to identified

    return
    tail_label: list, a list containing column name of all the tail label
    """
    columns = df.columns
    n = len(columns)
    irpl = np.zeros(n)
    for column in range(n):
        # print(column)
        # print(columns[column])
        # print(df[columns[column]].value_counts())
        vc = df[columns[column]].value_counts()
        if len(vc) > 1:
            irpl[column] = vc[1]
        else:
            print(f"Column {columns[column]} without examples!")
            irpl[column] = 0
    irpl = max(irpl) / [i if i > 0 else 1 for i in irpl]
    # print(irpl)
    mir = np.average(irpl)
    # print(mir)
    tail_label = []
    for i in range(n):
        if irpl[i] > mir:
            tail_label.append(columns[i])
    return tail_label


def get_index(df):
    """
    give the index of all tail_label rows
    args
    df: pandas.DataFrame, target label df from which index for tail label has to identified

    return
    index: list, a list containing index number of all the tail label
    """
    tail_labels = get_tail_label(df)
    # print(f"Tail labels {tail_labels}")
    index = set()
    for tail_label in tail_labels:
        sub_index = set(df[df[tail_label] == 1].index)
        index = index.union(sub_index)
    return list(index)


def get_minority_instace(X, y):
    """
    Give minority dataframe containing all the tail labels

    args
    X: pandas.DataFrame, the feature vector dataframe
    y: pandas.DataFrame, the target vector dataframe

    return
    X_sub: pandas.DataFrame, the feature vector minority dataframe
    y_sub: pandas.DataFrame, the target vector minority dataframe
    """
    index = get_index(y)
    X_sub = X[X.index.isin(index)].reset_index(drop=True)
    y_sub = y[y.index.isin(index)].reset_index(drop=True)
    return X_sub, y_sub


def nearest_neighbour(X):
    """
    Give index of 5 nearest neighbor of all the instance

    args
    X: np.array, array whose nearest neighbor has to find

    return
    indices: list of list, index of 5 NN of each element in X
    """
    nbs = NearestNeighbors(n_neighbors=5, metric='euclidean', algorithm='kd_tree').fit(X)
    euclidean, indices = nbs.kneighbors(X)
    return indices


def augment(X, y, n_sample=None):
    """
    Give the augmented data using MLSMOTE algorithm

    args
    X: pandas.DataFrame, input vector DataFrame
    y: pandas.DataFrame, feature vector dataframe
    n_sample: int, number of newly generated sample

    return
    new_X: pandas.DataFrame, augmented feature vector data
    target: pandas.DataFrame, augmented target vector data
    """
    if n_sample is None:
        n_sample = len(y.columns) * 5
    indices2 = nearest_neighbour(X)
    n = len(indices2)
    new_X = np.zeros((n_sample, X.shape[1]))
    target = np.zeros((n_sample, y.shape[1]))
    for i in range(n_sample):
        reference = random.randint(0, n - 1)
        neighbour = random.choice(indices2[reference, 1:])
        all_point = indices2[reference]
        nn_df = y[y.index.isin(all_point)]
        ser = nn_df.sum(axis=0, skipna=True)
        target[i] = np.array([1 if val > 2 else 0 for val in ser])
        ratio = random.random()
        gap = X.loc[reference, :] - X.loc[neighbour, :]
        new_X[i] = np.array(X.loc[reference, :] + ratio * gap)
    new_X = pd.DataFrame(new_X, columns=X.columns)
    target = pd.DataFrame(target, columns=y.columns)
    new_X = pd.concat([X, new_X], axis=0)
    target = pd.concat([y, target], axis=0)
    return new_X, target


def MLSMOTE(X, y, n_sample=None):
    print(f"IRMean {get_irlb(y)[1]} {len(X)} {len(y)}")
    X_sub, y_sub = get_minority_instace(X, y)
    X_res, y_res = augment(X_sub, y_sub, n_sample)
    X_res = pd.concat([X, X_res])
    y_res = pd.concat([y, y_res])
    irlb, irlb_mean_last = get_irlb(y_res)
    print(f"IRMean {irlb_mean_last} {len(X_res)} {len(y_res)}")
    return X_res, y_res


def MLSMOTE_iterative(X, y, threshold=None, cp=False):
    X_i = X
    y_i = y
    # setting seed for reproducibility purpose
    random.seed(42)
    #print(random.getstate())
    irlb, irlb_mean_last = get_irlb(y_i)
    print(f"Initial Avg. Imbalance Ratio {irlb_mean_last}")
    while True:
        X_sub, y_sub = get_minority_instace(X_i, y_i)
        if cp:
            X_res, y_res = X_sub, y_sub
        else:
            X_res, y_res = augment(X_sub, y_sub)
        X_cur = pd.concat([X, X_res])
        y_cur = pd.concat([y, y_res])
        irlb, irlb_mean_cur = get_irlb(y_cur)
        print(f"Current Avg. Imbalance Ratio {irlb_mean_cur}")
        if (threshold is None and irlb_mean_cur < irlb_mean_last) \
                or (threshold is not None and irlb_mean_cur > threshold):
            X_i = X_cur
            y_i = y_cur
            irlb_mean_last = irlb_mean_cur
        else:
            print(f"Current Avg. Imbalance Ratio {irlb_mean_last}")
            break
    return X_i, y_i

if __name__ == '__main__':
    """
    main function to use the MLSMOTE
    """
    X, y = create_dataset()  # Creating a Dataframe
    print(X)
    print(y)
    #X_sub, y_sub = get_minority_instace(X, y)  # Getting minority instance of that datframe
    X_res, y_res = MLSMOTE(X, y, 100)  # Applying MLSMOTE to augment the dataframe