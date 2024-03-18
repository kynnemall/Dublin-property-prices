#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 16:11:17 2024

@author: martin
"""

import os
import mlflow
import dagshub
import pandas as pd
from sklearn import metrics
from sklearn import set_config
from sklearn.pipeline import Pipeline
from sklearn.linear_model import BayesianRidge, RidgeCV
from sklearn.compose import ColumnTransformer
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from dagshub.data_engine import datasources
set_config(transform_output="pandas")


def prepare_data():
    """
    Load all CSV data, drop duplicates by URL, apply constraints, format 
    categorical BER and make splits for training and evaluation.

    Returns
    -------
    X_train : pandas.DataFrame
        Formatted feature dataset for model training
    X_test : pandas.DataFrame
        Formatted feature dataset for model evaluation
    y_train : pandas.Series
        Target variable for model training
    y_test : pandas.Series
        Target variable for model evaluation

    """

    # load all datasets
    source = datasources.get_datasources(
        'kynnemall/Dublin-property-prices'
    )[-1]
    dags_df = source.all().dataframe
    csvs_df = dags_df[dags_df["path"].str.endswith("properties.csv")]
    csv_links = csvs_df["dagshub_download_url"].values
    df = pd.concat([pd.read_csv(c) for c in csv_links])
    df.drop_duplicates(subset='url', keep='last', inplace=True)

    # keep properties with a sales price of maximum €800,000
    df = df[df['price'] <= 8e5]

    # make categoricalencoding of BER
    ordered_ber = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1',
                   'D2', 'E1', 'E2', 'F', 'G', 'Exempt']
    df['ber'] = pd.Categorical(df['ber'], categories=ordered_ber)
    df['ber'] = df['ber'].cat.codes
    df.dropna(inplace=True)

    X = df[['bathrooms', 'bedrooms', 'ber', 'postcode', 'property_type']]
    y = df['price']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, stratify=X['postcode'], random_state=42, test_size=0.2
    )

    return X_train, X_test, y_train, y_test


# %%
if __name__ == "__main__":
    dagshub.auth.add_app_token(token=os.environ["TOKEN"])
    dagshub.init(repo_name="Dublin-property-prices", repo_owner="kynnemall",
                 mlflow=True)
    mlflow.set_tracking_uri(
        "https://dagshub.com/kynnemall/Dublin-property-prices.mlflow"
    )

    # no need to start or end logging
    mlflow.sklearn.autolog()

    # %% one-hot encode step for postcodes and property types
    columns_to_encode = ["postcode", "property_type"]
    onehot_step = ColumnTransformer(
        transformers=[(
            'onehot', OneHotEncoder(
                sparse_output=False, handle_unknown="infrequent_if_exist",
                min_frequency=10), columns_to_encode
        )], remainder='passthrough'
    )

    # scale continuous features
    columns_to_scale = ['remainder__' +
                        c for c in ('ber', 'bathrooms', 'bedrooms')]
    scale_step = ColumnTransformer(
        transformers=[
            ('scale', StandardScaler(), columns_to_scale),
        ], remainder='passthrough'
    )

    clfs = (
        RidgeCV(cv=10),
        DecisionTreeRegressor(random_state=42, min_impurity_decrease=10e3),
        RandomForestRegressor(
            10, random_state=42, min_impurity_decrease=10e3, n_jobs=-1
        ),
        BayesianRidge(),
    )
    names = (
        "Ridge Regression with CV",
        "Decision Tree",
        "Random Forest",
        "Bayesian Ridge Regression",
    )

    # prepare train and test datasets
    X_train, X_test, y_train, y_test = prepare_data()
    for clf, name in zip(clfs, names):
        model = Pipeline([
            ('onehot-preprocessor', onehot_step),
            ('scale-continuous', scale_step),
            ('clf', clf),
        ])

        model.fit(X_train, y_train)
        model.score(X_train, y_train)
        model.score(X_test, y_test)

        test_pred = model.predict(X_test)
        train_pred = model.predict(X_train)
        test_mse = metrics.mean_squared_error(y_test, test_pred)
        test_mae = metrics.mean_absolute_error(y_test, test_pred)
        train_mae = metrics.mean_absolute_error(y_train, train_pred)

        print(f"\n{name}")
        print(f"Train score:\t{model.score(X_train, y_train):.2f}")
        print(f"Test score:\t{model.score(X_test, y_test):.2f}")
        print(f"Train MAE\t{train_mae:.2f}")
        print(f"Test MAE\t\t{test_mae:.2f}")
