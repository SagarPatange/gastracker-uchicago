#!/bin/bash

# Gas Tracker - Quick Setup Script
# Run this to deploy to Streamlit Cloud

echo "╔═══════════════════════════════════════════════════════╗"
echo "║     Gas Tracker Dashboard - Quick Setup               ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Installing..."
    brew install git
fi

echo "✅ Git is installed"
echo ""

# Configure git if not already configured
if [ -z "$(git config --global user.name)" ]; then
    echo "📝 Setting up Git..."
    read -p "Enter your name: " git_name
    read -p "Enter your email: " git_email
    git config --global user.name "$git_name"
    git config --global user.email "$git_email"
    echo "✅ Git configured"
fi

echo ""
echo "🚀 Initializing repository..."
git init
git add .
git commit -m "Gas Tracker Dashboard - Initial commit"
echo "✅ Repository initialized"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Go to: https://github.com/new"
echo "2. Repository name: gastracker-uchicago"
echo "3. Make it PUBLIC"
echo "4. Click 'Create repository'"
echo ""
echo "5. Then run these commands:"
echo ""
read -p "Enter your GitHub username: " github_username
echo ""
echo "   git remote add origin https://github.com/$github_username/gastracker-uchicago.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "6. Deploy to Streamlit:"
echo "   Go to: https://share.streamlit.io"
echo "   Click 'New app'"
echo "   Select your repo"
echo "   Click 'Deploy!'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Ready to deploy!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
