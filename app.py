import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import time
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Gas Inventory Manager",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .big-metric {
        font-size: 2rem;
        font-weight: bold;
    }
    .critical-alert {
        background-color: #ff4b4b;
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
    }
    .warning-alert {
        background-color: #ffa500;
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar - File Upload
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.markdown("---")
    
    # File upload
    st.subheader("📁 Upload Excel File")
    
    st.info("""
    **Upload your gas inventory Excel file:**
    - Must have columns: Room, Gas_Type, PSI
    - Optional: Full, Empty, Days_Remaining, Last_Updated
    """)
    
    uploaded_file = st.file_uploader(
        "Choose Excel file",
        type=['xlsx', 'xls'],
        help="Upload your gas inventory spreadsheet"
    )
    
    st.markdown("---")
    
    # Auto-refresh settings
    st.subheader("🔄 Auto-Refresh")
    auto_refresh = st.checkbox("Enable auto-refresh", value=False)
    if auto_refresh:
        refresh_interval = st.slider("Refresh every (seconds):", 10, 120, 30)
    
    st.markdown("---")
    
    # Download sample template
    st.subheader("📊 Sample Template")
    
    # Create sample data
    sample_data = pd.DataFrame({
        'Room': [208, 292, 306, 315, 401],
        'Gas_Type': ['Argon', 'Helium', 'Nitrogen', 'Argon', 'Oxygen'],
        'PSI': [450, 200, 1500, 750, 1200],
        'Full': [2, 0, 3, 1, 2],
        'Empty': [1, 3, 0, 2, 1],
        'Days_Remaining': [4.5, 2.0, 15.0, 7.5, 12.0],
        'Last_Updated': ['2024-11-14'] * 5
    })
    
    # Create download buffer
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sample_data.to_excel(writer, index=False, sheet_name='Inventory')
    
    st.download_button(
        label="📥 Download Sample Template",
        data=output.getvalue(),
        file_name="Gas_Inventory_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Main content
st.title("🔬 Gas Inventory Dashboard")
st.caption(f"Dashboard updated: {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}")

# Load data function
@st.cache_data(ttl=30)
def load_inventory(file):
    """Load inventory data from uploaded Excel file"""
    try:
        df = pd.read_excel(file)
        
        # Ensure required columns exist
        required_columns = ['Room', 'Gas_Type', 'PSI']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"❌ Missing required column: {col}")
                return None
        
        # Calculate days remaining if not present
        if 'Days_Remaining' not in df.columns:
            # Simple estimation: PSI / 100 = days (adjust based on actual consumption)
            df['Days_Remaining'] = (df['PSI'] / 100).round(1)
        
        return df
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {e}")
        st.info("Make sure your Excel file has columns: Room, Gas_Type, PSI")
        return None

# Check if file is uploaded
if uploaded_file is None:
    st.warning("👈 **Please upload your Excel file in the sidebar to get started**")
    
    st.markdown("---")
    st.subheader("📋 Quick Setup Instructions")
    st.markdown("""
    1. Look at the **left sidebar** (click ☰ if hidden)
    2. Click **"Browse files"** under "Upload Excel file"
    3. Select your gas inventory Excel file
    4. Your dashboard will load automatically!
    
    **Don't have a file yet?** Download the sample template from the sidebar!
    """)
    
    st.markdown("---")
    st.subheader("📊 Expected Excel Format")
    st.markdown("""
    Your Excel file should have these columns:
    - **Room**: Room number (e.g., 208, 292)
    - **Gas_Type**: Type of gas (e.g., Argon, Helium)
    - **PSI**: Current pressure (e.g., 450, 1200)
    - **Full** (optional): Number of full cylinders
    - **Empty** (optional): Number of empty cylinders
    - **Days_Remaining** (optional): Estimated days until stockout
    """)
    
    # Show sample data
    st.dataframe(sample_data, use_container_width=True, hide_index=True)
    
    st.stop()

# Load the data
df = load_inventory(uploaded_file)

if df is None:
    st.stop()

# Calculate categories
critical = df[df['PSI'] < 500]
warning = df[(df['PSI'] >= 500) & (df['PSI'] < 1000)]
stable = df[df['PSI'] >= 1000]

# Top metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="🔴 CRITICAL - Order NOW",
        value=len(critical),
        delta=f"{len(critical)} rooms need immediate attention" if len(critical) > 0 else "All clear",
        delta_color="inverse"
    )

with col2:
    st.metric(
        label="🟡 WARNING - Order This Week",
        value=len(warning),
        delta=f"{len(warning)} rooms to monitor" if len(warning) > 0 else "All clear",
        delta_color="inverse"
    )

with col3:
    st.metric(
        label="🟢 STABLE",
        value=len(stable),
        delta=f"{len(stable)} rooms in good condition",
        delta_color="normal"
    )

st.markdown("---")

# Critical alerts section
if len(critical) > 0:
    st.error("⚠️ **IMMEDIATE ACTION REQUIRED**")
    st.markdown("### 🔴 Critical Rooms (PSI < 500)")
    
    # Sort by PSI ascending (most critical first)
    critical_sorted = critical.sort_values('PSI')
    
    st.dataframe(
        critical_sorted[['Room', 'Gas_Type', 'PSI', 'Days_Remaining']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Room": st.column_config.TextColumn("Room #", width="small"),
            "Gas_Type": st.column_config.TextColumn("Gas Type", width="medium"),
            "PSI": st.column_config.NumberColumn("PSI", width="small", format="%d"),
            "Days_Remaining": st.column_config.NumberColumn("Days Left", width="small", format="%.1f")
        }
    )
    
    st.markdown("---")

# Warning section
if len(warning) > 0:
    st.warning("📋 **Order These This Week**")
    st.markdown("### 🟡 Warning Rooms (PSI 500-1000)")
    
    warning_sorted = warning.sort_values('PSI')
    
    st.dataframe(
        warning_sorted[['Room', 'Gas_Type', 'PSI', 'Days_Remaining']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Room": st.column_config.TextColumn("Room #", width="small"),
            "Gas_Type": st.column_config.TextColumn("Gas Type", width="medium"),
            "PSI": st.column_config.NumberColumn("PSI", width="small", format="%d"),
            "Days_Remaining": st.column_config.NumberColumn("Days Left", width="small", format="%.1f")
        }
    )
    
    st.markdown("---")

# Stable rooms
if len(stable) > 0:
    st.success(f"✅ **{len(stable)} Rooms in Good Condition**")
    
    with st.expander("📊 View Stable Rooms (PSI > 1000)", expanded=False):
        stable_sorted = stable.sort_values('PSI', ascending=False)
        st.dataframe(
            stable_sorted[['Room', 'Gas_Type', 'PSI', 'Days_Remaining']],
            use_container_width=True,
            hide_index=True
        )

# Full inventory view
st.markdown("---")
with st.expander("📋 View Complete Inventory", expanded=False):
    st.dataframe(
        df.sort_values('PSI'),
        use_container_width=True,
        hide_index=True
    )

# Summary statistics
st.markdown("---")
st.subheader("📊 Inventory Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Rooms", len(df))

with col2:
    st.metric("Gas Types", df['Gas_Type'].nunique())

with col3:
    st.metric("Avg PSI", f"{df['PSI'].mean():.0f}")

with col4:
    if 'Days_Remaining' in df.columns:
        st.metric("Avg Days Left", f"{df['Days_Remaining'].mean():.1f}")

# Auto-refresh logic
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
