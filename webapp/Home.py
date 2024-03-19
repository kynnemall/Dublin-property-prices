#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 16:23:44 2024

@author: martin
"""

import mlflow
import pandas as pd
import streamlit as st
from sklearn import set_config
from dagshub.auth import add_app_token
from dagshub.data_engine import datasources
set_config(transform_output="pandas")


def load_latest_dataset():
    if "listings" not in st.session_state:
        mlflow.set_tracking_uri(
            "https://dagshub.com/kynnemall/Dublin-property-prices.mlflow"
        )

        add_app_token(token=st.secrets["TOKEN"])
        source = datasources.get_datasources(
            'kynnemall/Dublin-property-prices'
        )[-1]
        dags_df = source.all().dataframe
        csvs_df = dags_df[dags_df["path"].str.endswith("properties.csv")]
        csv = csvs_df["dagshub_download_url"].iloc[-1]
        filename = csvs_df["path"].iloc[-1]

        df = pd.read_csv(csv)
        df["url"] = "https://www.property.ie/property-for-sale/" + df["url"]
        df["bathrooms"] = df["bathrooms"].astype(int)
        df["bedrooms"] = df["bedrooms"].astype(int)

        # prepare data for predictions
        # make categoricalencoding of BER
        ordered_ber = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1',
                       'D2', 'E1', 'E2', 'F', 'G', 'Exempt']
        df["BER"] = df["ber"]
        df['ber'] = pd.Categorical(df['ber'], categories=ordered_ber)
        df['ber'] = df['ber'].cat.codes
        X = df[['bathrooms', 'bedrooms', 'ber', 'postcode', 'property_type']]

        # get run id for best Bayesian Ridge model
        runs = mlflow.search_runs()
        runs = runs[runs["params.clf"].str.contains("Bay")]
        sort_cols = [c for c in runs.columns if "score" in c and "test" in c]
        runs.sort_values(sort_cols[0], inplace=True, ascending=False)
        run_id = runs["run_id"].iloc[0]

        # load model and predict scores with Bayesian prediction intervals
        model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")
        pred, pred_std = model.predict(X, return_std=True)

        df["price_pred"] = pred.astype(int)
        df['error'] = df['price'] - df['price_pred']
        df["price_pred_std"] = pred_std

        st.session_state["listings"] = df
        st.session_state["date"] = filename.split('_')[0]


st.markdown(
    """
    Want to buy a home but having trouble comparing properties?

    Then this is the app for you!

    We have curated property listings and harnessed the power of AI
    to predict prices and determine if properties are being sold for more
    than they should be, or if you may have found a bargain!

    Filter Listings interactively to shortlist houses, apartments, and more!
    
    
    """
)

load_latest_dataset()
st.markdown(f"Property listings last updated on {st.session_state['date']}")
