# 🚀 QUICK DEPLOYMENT GUIDE

## ⚡ 5-Minute Deploy to Streamlit Cloud

### STEP 1: Push to GitHub (2 min)

```bash
cd GasTracker_Cloud_Ready

# Initialize git
git init
git add .
git commit -m "Gas Tracker Dashboard - Initial commit"

# Create repo on GitHub (github.com → New repository)
# Name: gastracker-uchicago
# Public repo

# Push to GitHub
git remote add origin https://github.com/YOUR-USERNAME/gastracker-uchicago.git
git branch -M main
git push -u origin main
```

### STEP 2: Deploy to Streamlit (2 min)

1. Go to: **https://share.streamlit.io**
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repo: `YOUR-USERNAME/gastracker-uchicago`
5. Branch: `main`
6. Main file: `app.py`
7. Click **"Deploy!"**

### STEP 3: Get Your URL (1 min)

Your app will be live at:
```
https://your-app-name.streamlit.app
```

Bookmark this and send to building manager!

---

## 🔐 After Funding Approval: Add Security

### Upgrade to Teams ($20/month)

1. Settings → Billing → **"Upgrade to Teams"**
2. Enter payment info
3. Subscribe

### Enable Password Protection

1. App Settings → **Sharing**
2. Toggle **"Require viewers to log in"**
3. Add authorized emails
4. Save

Done! Now only authorized users can access.

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] App deployed to Streamlit Cloud
- [ ] URL accessible in browser
- [ ] File upload tested
- [ ] Alerts display correctly
- [ ] Building manager notified
- [ ] (After funding) Upgraded to Teams
- [ ] (After funding) Password protection enabled

---

## 🆘 Troubleshooting

**Build failed?**
- Check logs in Streamlit dashboard
- Verify requirements.txt is correct

**Module not found?**
- Add missing package to requirements.txt
- Push update to GitHub (auto-redeploys)

**Can't upload file?**
- Check file is .xlsx or .xls
- Verify file size < 200 MB

---

**That's it! You're live in 5 minutes! 🎉**
