# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

import streamlit as st
import datetime

# --- Page Configuration ---
st.set_page_config(page_title="My Patient Advocate", page_icon="🛡️", layout="centered")

# --- Title & Privacy Warning ---
st.title("🛡️ Patient Advocate: ROI Generator")
st.warning("⚠️ PRIVACY NOTICE: This tool runs 100% locally. No data leaves your device.")
st.divider()

# --- Sidebar with Source Link (AGPL Requirement) ---
with st.sidebar:
    st.header("About")
    st.markdown(
        """
        This app is open source under the **GNU AGPLv3**.
        
        [View Source Code on GitHub](https://github.com/Lilian-Moon11/local-patient-advocate)
        """
    )

# --- The Form ---
with st.form("roi_form"):
    st.write("### 1. Patient Information")
    col1, col2 = st.columns(2)
    with col1:
        patient_name = st.text_input("Full Name")
        dob = st.date_input("Date of Birth", min_value=datetime.date(1920, 1, 1))
    with col2:
        mrn = st.text_input("Medical Record Number (Optional)")
        
    st.write("### 2. Request Details")
    hospital_name = st.text_input("Hospital Name")
    records_type = st.multiselect("Records Requested", ["Discharge Summary", "Labs", "Imaging", "All Records"])
    
    submitted = st.form_submit_button("Generate Official Form")

if submitted:
    st.success("Form Generated!")
    report = f"""
    OFFICIAL RELEASE OF INFORMATION
    To: {hospital_name}
    From: {patient_name} (DOB: {dob})
    Requesting: {", ".join(records_type)}
    """
    st.code(report, language="text")