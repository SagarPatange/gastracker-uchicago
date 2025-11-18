import tempfile
import shutil
from pathlib import Path

# Import backend modules
import sys
sys.path.append(str(Path(__file__).parent))
from backend.src.priority2_adaptive_predictor import AdaptivePredictor
from backend.src.priority3_order_optimizer import OrderOptimizer

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import time
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="ERC Gas Tracker | UChicago",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load external CSS
def load_css(file_name):
    """Load CSS from external file"""
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"⚠️ CSS file '{file_name}' not found. Using default styling.")

# Load custom styles
load_css('style.css')

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

# Main Header
col_logo, col_title = st.columns([1, 5])
with col_title:
    st.title("⚗️ Gas Inventory Dashboard")
    st.markdown("**University of Chicago** | Energy Research Center")
st.caption(f"Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}")
st.markdown("---")

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
                return None, None
        
        # Calculate days remaining if not present
        if 'Days_Remaining' not in df.columns:
            # Simple estimation: PSI / 100 = days (adjust based on actual consumption)
            df['Days_Remaining'] = (df['PSI'] / 100).round(1)
        
        return df, file
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {e}")
        st.info("Make sure your Excel file has columns: Room, Gas_Type, PSI")
        return None, None

@st.cache_data(ttl=30)
def run_backend_analysis(file_bytes):
    """Run the adaptive predictor on uploaded file"""
    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save uploaded file to temp location
            temp_path = Path(tmpdir) / "inventory_levels.xlsx"
            with open(temp_path, 'wb') as f:
                f.write(file_bytes.getvalue())
            
            # Run adaptive predictor
            predictor = AdaptivePredictor(excel_path=str(temp_path))
            forecast = predictor.generate_weekly_forecast()
            
            # Run order optimizer
            # Save forecast temporarily for optimizer
            forecast_path = Path(tmpdir) / "weekly_forecast.json"
            with open(forecast_path, 'w') as f:
                json.dump(forecast, f)
            
            # Create outputs directory
            outputs_dir = Path(tmpdir) / "outputs"
            outputs_dir.mkdir(exist_ok=True)
            shutil.copy(forecast_path, outputs_dir / "weekly_forecast.json")
            
            # Run optimizer
            optimizer = OrderOptimizer()
            optimizer.forecast = forecast  # Pass forecast directly
            action_plan = optimizer.generate_action_plan()
            
            return forecast, action_plan
    except Exception as e:
        st.error(f"❌ Error running predictions: {e}")
        return None, None

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
df, uploaded_file_bytes = load_inventory(uploaded_file)

if df is None:
    st.stop()

# Run backend predictions
with st.spinner("🔮 Running smart predictions..."):
    forecast, action_plan = run_backend_analysis(uploaded_file)

# Calculate categories (basic thresholds)
critical = df[df['PSI'] < 500]
warning = df[(df['PSI'] >= 500) & (df['PSI'] < 1000)]
stable = df[df['PSI'] >= 1000]

# Top metrics - Enhanced with better labels
st.markdown("### 📊 Current Status Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🔴 CRITICAL")
    st.metric(
        label="Immediate Action Required",
        value=len(critical),
        delta=f"-{len(critical)} rooms" if len(critical) > 0 else "All clear ✓",
        delta_color="inverse"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🟡 WARNING")
    st.metric(
        label="Order This Week",
        value=len(warning),
        delta=f"-{len(warning)} rooms" if len(warning) > 0 else "All clear ✓",
        delta_color="inverse"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🟢 STABLE")
    st.metric(
        label="Good Condition",
        value=len(stable),
        delta=f"+{len(stable)} rooms",
        delta_color="normal"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Smart Predictions Banner (if available)
if forecast and action_plan:
    st.markdown("---")
    st.markdown("### 🔮 AI-Powered Predictions")
    st.markdown("*Predictive analytics based on historical consumption patterns*")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        urgent_orders = len(action_plan.get('immediate_actions', []))
        st.metric(
            label="⚡ Urgent Orders (Monday)",
            value=urgent_orders,
            delta=f"{urgent_orders} rooms need ordering NOW" if urgent_orders > 0 else "None",
            delta_color="inverse"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        routine_orders = len(action_plan.get('routine_orders', []))
        st.metric(
            label="📋 Routine Orders (This Week)",
            value=routine_orders,
            delta=f"Can batch order Thursday" if routine_orders > 0 else "None",
            delta_color="normal"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        savings = action_plan.get('savings', {}).get('total_weekly_savings', 0)
        st.metric(
            label="💰 Estimated Weekly Savings",
            value=f"${savings:.0f}",
            delta="vs reactive ordering"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Show immediate action items
    if action_plan.get('immediate_actions'):
        st.markdown('<div class="critical-alert">', unsafe_allow_html=True)
        st.markdown("### ⚡ MONDAY MORNING ACTION ITEMS")
        for action in action_plan['immediate_actions']:
            room = action['room']
            reason = action['reason']
            qty = action.get('quantity', 1)
            st.markdown(f"**• {room}**: Order {qty} cylinder(s) - *{reason}*")
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Critical alerts section
if len(critical) > 0:
    st.markdown('<div class="critical-alert">', unsafe_allow_html=True)
    st.markdown("### ⚠️ IMMEDIATE ACTION REQUIRED")
    st.markdown("#### 🔴 Critical Rooms (PSI < 500)")
    st.markdown('</div>', unsafe_allow_html=True)
    
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
    st.markdown('<div class="warning-alert">', unsafe_allow_html=True)
    st.markdown("### 📋 Order These This Week")
    st.markdown("#### 🟡 Warning Rooms (PSI 500-1000)")
    st.markdown('</div>', unsafe_allow_html=True)
    
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
    st.markdown('<div class="success-alert">', unsafe_allow_html=True)
    st.markdown(f"### ✅ {len(stable)} Rooms in Good Condition")
    st.markdown('</div>', unsafe_allow_html=True)
    
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
st.markdown("### 📊 Inventory Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.metric("Total Rooms", len(df))
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.metric("Gas Types", df['Gas_Type'].nunique())
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.metric("Avg PSI", f"{df['PSI'].mean():.0f}")
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if 'Days_Remaining' in df.columns:
        st.metric("Avg Days Left", f"{df['Days_Remaining'].mean():.1f}")
    st.markdown('</div>', unsafe_allow_html=True)

# Detailed Forecast View
if forecast:
    st.markdown("---")
    with st.expander("🔮 7-Day Smart Forecast (AI Predictions)", expanded=False):
        st.markdown("**Predictive analytics based on historical consumption patterns**")
        
        for room, data in forecast.get('room_forecasts', {}).items():
            if 'error' not in data:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown(f"#### {room}")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Current PSI", f"{data.get('current_psi', 0):.0f}")
                
                with col2:
                    regime = data.get('regime', 'UNKNOWN')
                    regime_emoji = "🔥" if regime == "HIGH_EXPERIMENT" else "✅" if regime == "NORMAL" else "💤"
                    st.metric("Operating Mode", f"{regime_emoji} {regime}")
                
                with col3:
                    st.metric("Daily Burn Rate", f"{data.get('avg_daily_burn', 0):.0f} PSI/day")
                
                with col4:
                    days_left = data.get('days_until_critical', 999)
                    color = "🔴" if days_left < 2 else "🟡" if days_left < 5 else "🟢"
                    st.metric("Days to Critical", f"{color} {days_left:.1f}")
                
                # Recommendation with proper styling
                recommendation = data.get('recommendation', 'UNKNOWN')
                rec_text = recommendation.replace('_', ' ').title()
                
                if recommendation == 'SWAP_IMMEDIATELY':
                    st.markdown(f'<div class="critical-alert">🚨 <strong>{rec_text}</strong></div>', unsafe_allow_html=True)
                elif recommendation in ['ORDER_TODAY_URGENT', 'ORDER_THIS_WEEK']:
                    st.markdown(f'<div class="warning-alert">⚠️ <strong>{rec_text}</strong></div>', unsafe_allow_html=True)
                elif recommendation == 'MONITOR_CLOSELY':
                    st.info(f"👀 **{rec_text}**")
                else:
                    st.markdown(f'<div class="success-alert">✅ <strong>{rec_text}</strong></div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("---")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #767676; padding: 20px;">
    <small>Gas Tracker Dashboard | University of Chicago Energy Research Center<br>
    Built with ❤️ for building management efficiency</small>
</div>
""", unsafe_allow_html=True)

# Auto-refresh logic
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()