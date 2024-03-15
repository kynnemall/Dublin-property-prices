#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 16:23:44 2024

@author: martin
"""

import pandas as pd
import streamlit as st
from dagshub.data_engine import datasources


@st.cache_data
def load_latest_dataset():
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
    return df, filename


st.markdown(
    """
    
            
    """
)


listings, fname = load_latest_dataset()
date = fname.split('_')[0]
st.session_state['listings'] = listings
st.text(f"Latest property listings acquired on {date}")
