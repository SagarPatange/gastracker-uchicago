import tempfile
import shutil
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

try:
    from backend.src.priority2_adaptive_predictor import AdaptivePredictor
    from backend.src.priority3_order_optimizer import OrderOptimizer
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

import streamlit as st
import pandas as pd
import json
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

load_css('style.css')

# Sidebar
with st.sidebar:
    # Branded Sidebar Header
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem; 
                background: linear-gradient(135deg, #800000 0%, #600000 100%); 
                border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">⚗️</div>
        <h2 style="color: white; margin: 0; font-size: 1.3rem;">Gas Tracker</h2>
        <p style="color: white; opacity: 0.9; margin: 0.5rem 0 0 0; font-size: 0.85rem;">
            UChicago Energy Research Center
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # File upload
    st.subheader("📁 Upload Data")
    
    st.info("""
    **Required Excel columns:**
    - Room, Gas_Type, PSI
    
    **Optional:**
    - Full, Empty, Days_Remaining
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
    st.subheader("📥 Sample Template")
    
    sample_data = pd.DataFrame({
        'Room': [208, 292, 306, 315, 401],
        'Gas_Type': ['Argon', 'Helium', 'Nitrogen', 'Argon', 'Oxygen'],
        'PSI': [450, 200, 1500, 750, 1200],
        'Full': [2, 0, 3, 1, 2],
        'Empty': [1, 3, 0, 2, 1],
        'Days_Remaining': [4.5, 2.0, 15.0, 7.5, 12.0],
        'Last_Updated': ['2024-11-14'] * 5
    })
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sample_data.to_excel(writer, index=False, sheet_name='Inventory')
    
    st.download_button(
        label="📥 Download Template",
        data=output.getvalue(),
        file_name="Gas_Inventory_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: #f8f9fa; 
                border-radius: 8px; font-size: 0.75rem; color: #767676;">
        <strong>Need Help?</strong><br>
        Contact: Building Management<br>
        v1.0 | Built with Streamlit
    </div>
    """, unsafe_allow_html=True)

# Main Header
st.markdown("""
<div class="hero-section">
    <h2>🎯 Real-Time Gas Cylinder Monitoring</h2>
    <p>Prevent research disruptions with AI-powered inventory tracking and predictive alerts</p>
</div>
""", unsafe_allow_html=True)

# Load data function
@st.cache_data(ttl=30)
def load_inventory(file):
    """Load inventory data from uploaded Excel file"""
    try:
        df = pd.read_excel(file)
        
        required_columns = ['Room', 'Gas_Type', 'PSI']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"❌ Missing required column: {col}")
                return None, None
        
        if 'Days_Remaining' not in df.columns:
            df['Days_Remaining'] = (df['PSI'] / 100).round(1)
        
        return df, file
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {e}")
        st.info("Make sure your Excel file has columns: Room, Gas_Type, PSI")
        return None, None

@st.cache_data(ttl=30)
def run_backend_analysis(file_bytes):
    """Run the adaptive predictor on uploaded file"""
    if not BACKEND_AVAILABLE:
        return None, None
        
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "inventory_levels.xlsx"
            with open(temp_path, 'wb') as f:
                f.write(file_bytes.getvalue())
            
            predictor = AdaptivePredictor(excel_path=str(temp_path))
            forecast = predictor.generate_weekly_forecast()
            
            forecast_path = Path(tmpdir) / "weekly_forecast.json"
            with open(forecast_path, 'w') as f:
                json.dump(forecast, f)
            
            outputs_dir = Path(tmpdir) / "outputs"
            outputs_dir.mkdir(exist_ok=True)
            shutil.copy(forecast_path, outputs_dir / "weekly_forecast.json")
            
            optimizer = OrderOptimizer()
            optimizer.forecast = forecast
            action_plan = optimizer.generate_action_plan()
            
            return forecast, action_plan
    except Exception as e:
        st.error(f"❌ Error running predictions: {e}")
        return None, None

# Check if file is uploaded
if uploaded_file is None:
    # Enhanced Empty State
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">📊</div>
        <h2>Welcome to the Gas Tracker Dashboard</h2>
        <p style="font-size: 1.1rem; color: #767676; margin: 1rem 0;">
            Upload your Excel file to get started with real-time monitoring
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3 style="color: #800000; margin-top: 0;">📋 Quick Start Guide</h3>
            <ol style="line-height: 2; font-size: 1.05rem;">
                <li><strong>Open sidebar</strong> - Click ☰ if hidden</li>
                <li><strong>Upload file</strong> - Click "Browse files"</li>
                <li><strong>View dashboard</strong> - Automatic analysis</li>
            </ol>
            
            <hr style="margin: 1.5rem 0;">
            
            <h4 style="color: #800000;">📊 Required Excel Format</h4>
            <table style="width: 100%; margin: 1rem 0;">
                <tr style="background: #f8f9fa;">
                    <th style="padding: 0.5rem; text-align: left;">Column</th>
                    <th style="padding: 0.5rem; text-align: left;">Example</th>
                </tr>
                <tr>
                    <td style="padding: 0.5rem;"><strong>Room</strong></td>
                    <td style="padding: 0.5rem;">208, 292, 306</td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 0.5rem;"><strong>Gas_Type</strong></td>
                    <td style="padding: 0.5rem;">Argon, Helium</td>
                </tr>
                <tr>
                    <td style="padding: 0.5rem;"><strong>PSI</strong></td>
                    <td style="padding: 0.5rem;">450, 1200</td>
                </tr>
            </table>
            
            <div style="background: #fff5f5; padding: 1rem; border-radius: 8px; 
                        border-left: 4px solid #800000; margin-top: 1.5rem;">
                <strong style="color: #800000;">💡 Pro Tip:</strong><br>
                Don't have a file? Download the sample template from the sidebar!
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.stop()

# Load the data with nice loading animation
with st.spinner(""):
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <div style="font-size: 3rem; animation: pulse 1.5s ease-in-out infinite;">⚗️</div>
        <h3>Analyzing your inventory...</h3>
        <p style="color: #767676;">Running diagnostics and generating insights</p>
    </div>
    <style>
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.1); }
        }
    </style>
    """, unsafe_allow_html=True)
    
    df, uploaded_file_bytes = load_inventory(uploaded_file)
    forecast, action_plan = run_backend_analysis(uploaded_file) if BACKEND_AVAILABLE else (None, None)

if df is None:
    st.stop()

# Calculate categories
critical = df[df['PSI'] < 500]
warning = df[(df['PSI'] >= 500) & (df['PSI'] < 1000)]
stable = df[df['PSI'] >= 1000]

# Overall Status Banner
if len(critical) > 0:
    st.markdown(f"""
    <div class="critical-alert" style="text-align: center; font-size: 1.1rem;">
        🚨 <strong>ALERT:</strong> {len(critical)} room(s) need immediate attention!
    </div>
    """, unsafe_allow_html=True)
elif len(warning) > 0:
    st.markdown(f"""
    <div class="warning-alert" style="text-align: center; font-size: 1.1rem;">
        ⚠️ {len(warning)} room(s) need ordering this week
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="success-alert" style="text-align: center; font-size: 1.1rem;">
        ✅ All systems operational - No urgent actions needed
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Top metrics with enhanced cards
st.markdown("### 📊 Current Status Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🔴 CRITICAL")
    st.metric(
        label="Immediate Action",
        value=len(critical),
        delta=f"{len(critical)} rooms" if len(critical) > 0 else "All clear ✓",
        delta_color="inverse",
        help="Rooms with PSI below 500 need cylinder replacement TODAY"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🟡 WARNING")
    st.metric(
        label="Order This Week",
        value=len(warning),
        delta=f"{len(warning)} rooms" if len(warning) > 0 else "All clear ✓",
        delta_color="inverse",
        help="Rooms with PSI 500-1000 need ordering within 3-5 days"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🟢 STABLE")
    st.metric(
        label="Good Condition",
        value=len(stable),
        delta=f"{len(stable)} rooms",
        delta_color="normal",
        help="Rooms with PSI above 1000 are in good condition"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# AI Predictions Section
if forecast and action_plan:
    st.markdown("---")
    st.markdown("### 🔮 AI-Powered Predictions")
    st.caption("*Predictive analytics based on historical consumption patterns*")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        urgent_orders = len(action_plan.get('immediate_actions', []))
        st.metric(
            label="⚡ Urgent Orders (Monday)",
            value=urgent_orders,
            delta="Immediate" if urgent_orders > 0 else "None"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        routine_orders = len(action_plan.get('routine_orders', []))
        st.metric(
            label="📋 Routine Orders",
            value=routine_orders,
            delta="Can batch Thursday" if routine_orders > 0 else "None"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        savings = action_plan.get('savings', {}).get('total_weekly_savings', 0)
        st.metric(
            label="💰 Weekly Savings",
            value=f"${savings:.0f}",
            delta="vs reactive ordering"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    if action_plan.get('immediate_actions'):
        st.markdown('<div class="critical-alert">', unsafe_allow_html=True)
        st.markdown("### ⚡ MONDAY MORNING ACTION ITEMS")
        for action in action_plan['immediate_actions']:
            st.markdown(f"**• {action['room']}**: Order {action.get('quantity', 1)} cylinder(s) - *{action['reason']}*")
        st.markdown('</div>', unsafe_allow_html=True)

# Quick Actions
if len(critical) > 0 or len(warning) > 0:
    st.markdown("---")
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📥 Download Order List", use_container_width=True):
            order_list = pd.concat([critical, warning])
            csv = order_list.to_csv(index=False)
            st.download_button(
                label="💾 Save as CSV",
                data=csv,
                file_name=f"gas_orders_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col2:
        if st.button("📊 Generate Report", use_container_width=True):
            st.success("✅ Report generated!")
    
    with col3:
        if st.button("📧 Email Alert", use_container_width=True):
            st.info("📬 Email prepared (demo mode)")
    
    with col4:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

st.markdown("---")

# Critical Section
if len(critical) > 0:
    st.markdown('<div class="critical-alert">', unsafe_allow_html=True)
    st.markdown("### ⚠️ IMMEDIATE ACTION REQUIRED")
    st.markdown("#### 🔴 Critical Rooms (PSI < 500)")
    st.markdown('</div>', unsafe_allow_html=True)
    
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

# Warning Section
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

# Stable Rooms
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

# Data Visualization
st.markdown("---")
st.markdown("### 📈 Inventory Analytics")

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### Status Distribution")
    status_data = pd.DataFrame({
        'Status': ['Critical', 'Warning', 'Stable'],
        'Count': [len(critical), len(warning), len(stable)]
    })
    st.bar_chart(status_data.set_index('Status'))
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### ⚠️ Top 5 Priority Rooms")
    top5 = df.nsmallest(5, 'PSI')[['Room', 'Gas_Type', 'PSI']]
    st.dataframe(top5, hide_index=True, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Complete Inventory
st.markdown("---")
with st.expander("📋 View Complete Inventory", expanded=False):
    st.dataframe(df.sort_values('PSI'), use_container_width=True, hide_index=True)

# Summary Statistics
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

# Detailed Forecast
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
                    emoji = "🔥" if regime == "HIGH_EXPERIMENT" else "✅" if regime == "NORMAL" else "💤"
                    st.metric("Mode", f"{emoji} {regime}")
                with col3:
                    st.metric("Daily Burn", f"{data.get('avg_daily_burn', 0):.0f} PSI/day")
                with col4:
                    days = data.get('days_until_critical', 999)
                    color = "🔴" if days < 2 else "🟡" if days < 5 else "🟢"
                    st.metric("Days to Critical", f"{color} {days:.1f}")
                
                recommendation = data.get('recommendation', 'UNKNOWN').replace('_', ' ').title()
                if 'SWAP' in recommendation or 'URGENT' in recommendation:
                    st.error(f"🚨 **{recommendation}**")
                elif 'ORDER' in recommendation or 'WEEK' in recommendation:
                    st.warning(f"⚠️ **{recommendation}**")
                else:
                    st.success(f"✅ **{recommendation}**")
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("---")

# Footer
st.markdown("""
<div class="footer">
    <small>
        <strong>Gas Tracker Dashboard</strong> | University of Chicago Energy Research Center<br>
        Built with ❤️ for building management efficiency | v1.0
    </small>
</div>
""", unsafe_allow_html=True)

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()