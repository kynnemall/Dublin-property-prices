#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 15 10:50:08 2024

@author: martin
"""

import streamlit as st
st.set_page_config(layout="wide")


def results_containers(listing, col):
    # define custom view options for the shortlisted data
    address = listing.url.split('/')[-3]
    nbed = listing.bedrooms
    nbath = listing.bathrooms
    price = listing.price
    ber = listing.BER
    diff = price - listing.price_pred
    diff_sign = 'lower' if diff > 0 else 'higher'
    color = 'green' if listing.price_pred < price else 'red'
    
    html = f"""
    <div style="text-decoration:none; border: 2px solid {color}; 
    border-radius: 10px; padding: 5px; margin: 5px;
    "><p><a href={listing.url}>{address}</a>
    <br>€{price:,.0f} (€{diff:,.0f} {diff_sign} than predicted)<br>{ber} BER, {nbed} Bedrooms, {nbath} Bathrooms</p></div>
    """
    col.markdown(html, unsafe_allow_html=True)


fdf = st.session_state["listings"]
fdf.dropna(inplace=True)

with st.expander("Filter Listings"):
    col1, col2 = st.columns(2)
    price_min, price_max = fdf["price"].min(), fdf["price"].max()
    price_filter = col1.slider("Filter by price (€)", price_min, price_max,
                               (price_min, price_max), step=1000)

    prop_options = sorted(fdf["property_type"].unique())
    prop_filter = col1.multiselect("proerty_type", prop_options)

    post_options = sorted(fdf["postcode"].unique())
    post_filter = col1.multiselect("Postcode", post_options)

    ber_options = sorted(fdf["BER"].unique())
    ber_filter = col2.multiselect("BER", ber_options)

    bed_min, bed_max = fdf["bedrooms"].min(), fdf["bedrooms"].max()
    bed_filter = col2.slider("Number of bedrooms", bed_min, bed_max,
                             (bed_min, bed_max), step=1)

    bath_min, bath_max = fdf["bathrooms"].min(), fdf["bathrooms"].max()
    bath_filter = col2.slider("Number of bathrooms", bath_min, bath_max,
                              (bath_min, bath_max), step=1)
    filtered = (fdf[
        (fdf["bedrooms"].between(*bed_filter, inclusive="both")) &
        (fdf["bathrooms"].between(*bath_filter, inclusive="both")) &
        (fdf["price"].between(*price_filter, inclusive="both"))
    ])
    if ber_filter:
        filtered = filtered[filtered["BER"].isin(ber_filter)]

    if post_filter:
        filtered = filtered[filtered["postcode"].isin(post_filter)]

    if prop_filter:
        filtered = filtered[filtered["property_type"].isin(prop_filter)]

    st.session_state["filtered"] = filtered

    sort_cols = fdf.columns[:-1].tolist()
    options = ["Bathrooms", "Bedrooms", "BER",
               "Postcode", "Price", "Property Type"]
    pretty_col = col1.selectbox("Sort by", options)
    sort_col = sort_cols[options.index(pretty_col)]
    asc = st.checkbox("Ascending by default", True)
    filtered.reset_index(inplace=True, drop=True)
    filtered.sort_values(sort_col, ascending=asc, inplace=True)

    st.markdown(
        f"<p style='text-align: center'>Total properties: {fdf.shape[0]}</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p style='text-align: center'>Remaining properties: {filtered.shape[0]}</p>",
        unsafe_allow_html=True
    )

with st.expander("Listings Results"):
    n_results = filtered.shape[0]
    n_pages = n_results // 20
    page = st.number_input("Results Page Number", 1, n_pages, 1, 1)
    st.markdown(f"Page {page} of {n_pages}")

    col_a, col_b = st.columns(2)
    for i, row in enumerate(filtered.iloc[page-1:page+19].itertuples(), 1):
        col = col_b if i > 10 else col_a
        results_containers(row, col)
