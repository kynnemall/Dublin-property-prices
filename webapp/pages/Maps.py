#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 15 10:50:08 2024

@author: martin
"""

import os
import numpy as np
import pydeck as pdk
import pandas as pd
import streamlit as st
from matplotlib import colors, cm


@st.cache_data
def prepare_mapdata():
    gdf = pd.read_csv('webapp/geodata.csv')
    df = st.session_state["listings"]
    g = df.groupby('postcode')['price'].median()
    g_pred = df.groupby('postcode')['pred'].median()

    # format postcodes for visualization
    codes = []
    for code in gdf['postcode'].str.split(',').str[0]:
        if code.startswith('Dub'):
            code = code.replace('ublin ', '')
            if len(code) == 2:
                code = code[0] + '0' + code[1]
        codes.append(code)

    # format price and apply log scale for visualization
    gdf['price'] = g[codes].values
    gdf['pred'] = g_pred[codes].values
    gdf['log'] = np.log10(gdf['price'])
    gdf['area'] = gdf['postcode'].str.split(',').str[0]
    gdf['scaled_price'] = (gdf['log'] - gdf['log'].min()) / \
        (gdf['log'].max() - gdf['log'].min())
    gdf['price'] = gdf['price'].apply(lambda x: f'€{x:,.0f}')
    gdf['pred'] = gdf['pred'].apply(lambda x: f'€{x:,.0f}')

    # map log-scaled prices to RGBA
    norm = colors.Normalize(vmin=0, vmax=1, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.Reds)
    gdf['fill_color'] = gdf['scaled_price'].map(
        lambda x: [int(c * 255) for c in mapper.to_rgba(x)])
    return gdf


mapdata = prepare_mapdata()

st.markdown("")

comp_view = pdk.data_utils.compute_view(mapdata[['lon', 'lat']])
st.pydeck_chart(pdk.Deck(
    map_style="dark",
    initial_view_state=comp_view,
    layers=[
        pdk.Layer(
            'ScatterplotLayer',
            data=mapdata,
            get_position='[lon, lat]',
            get_fill_color='fill_color',
            get_line_color=[0, 0, 0, 200],
            get_line_width=50,
            get_radius=300,
            pickable=True,
            auto_highlight=True,
        ),
    ],
    tooltip={
        "html": "<b>Area: </b> {area} <br>"
        "<b>Median Price: </b> {price} <br>"
        "<b>Predicted Price: </b> {pred}"}
))

# do something similar for st.session_state["filtered"]
