# 🔬 Gas Tracker Dashboard - Cloud Deployment

**Real-time gas cylinder inventory monitoring for UChicago ERC**

Live Dashboard: [Your app URL after deployment]

---

## 🚀 Quick Start for Users

1. **Visit the dashboard URL**
2. **Upload your Excel file** (click "Browse files" in sidebar)
3. **View alerts** - Red (urgent), Yellow (soon), Green (stable)

That's it!

---

## 📊 Excel File Format

Your Excel file must have these columns:

**Required:**
- `Room` - Room number (208, 292, etc.)
- `Gas_Type` - Gas name (Argon, Helium, etc.)
- `PSI` - Pressure level (450, 1200, etc.)

**Optional:**
- `Full` - Number of full cylinders
- `Empty` - Number of empty cylinders
- `Days_Remaining` - Estimated days left
- `Last_Updated` - Date of last update

See `Sample_Inventory.xlsx` for an example.

---

## 🎯 Alert Thresholds

| Color | PSI Range | Action |
|-------|-----------|--------|
| 🔴 Red | < 500 | Order TODAY |
| 🟡 Yellow | 500-1000 | Order this week |
| 🟢 Green | > 1000 | All good |

---

## 🛠️ For Developers

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py
```

### Deployment

This app is deployed on Streamlit Cloud.

**To deploy:**
1. Push to GitHub
2. Connect repo to Streamlit Cloud
3. Deploy!

See `DEPLOYMENT_GUIDE.md` for detailed instructions.

---

## 📧 Support

**Developer:** Saggy  
**Contact:** [Your email]

---

## 📄 License

Built for UChicago ERC Building Management
