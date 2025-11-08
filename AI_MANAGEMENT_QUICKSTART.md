# AI Management - Quick Start Guide

## 🚀 5-Minute Setup

### 1. Launch the UI
```bash
python app/launch.py
```
Opens at: http://localhost:8501

### 2. Navigate to AI Management
Click the **"🤖 AI Management"** tab (5th tab)

---

## 📋 Common Tasks

### Task 1: Edit AI Prompts
**Goal:** Change how the AI writes descriptions

1. Go to **AI Management** → **✏️ Prompt Editor**
2. Edit the text in the boxes:
   - **System Prompt**: AI's role/expertise
   - **User Prompt Template**: Instructions format
3. Click **💾 Gem Prompts**
4. Changes apply to next Step 4 run

**Example edit:**
```
Before: "You are an expert product description writer..."
After: "You are an expert B2B product description writer with 10 years of experience in industrial supplies..."
```

---

### Task 2: Set Golden Examples
**Goal:** Tell AI which products to use as examples

1. Go to **AI Management** → **⭐ Golden Examples**
2. Select a category (e.g., "5539 - Børster/Skrubber")
3. Check boxes for your best products (look for high quality scores)
4. Click **💾 Gem Golden Examples**
5. Next Step 4 run will prioritize these examples

**Tip:** Select 1-3 golden examples per category

---

### Task 3: Review AI Outputs
**Goal:** Approve good descriptions, reject bad ones

1. Go to **AI Management** → **📝 Review AI Outputs**
2. Use filters:
   - **Quality slider**: Show only high-quality products
   - **Approval filter**: See approved/rejected/pending
3. For each product:
   - Click tabs to see DESC_SHORT, DESC_LONG, etc.
   - Click **✅ Godkend** if good
   - Click **❌ Afvis** if bad
   - Click **🔄 Regenerer** to remake it

---

### Task 4: Regenerate with Feedback
**Goal:** Tell AI to improve a specific description

1. In **Review AI Outputs**, click **🔄 Regenerer** on a product
2. Type feedback in the box:
   - "Gør det mere teknisk"
   - "Tilføj information om miljøcertifikater"
   - "Forkorte til 150 ord max"
3. Click **▶️ Generer Med Feedback**
4. Wait 10-30 seconds
5. Page reloads with new description

---

## 🎯 Best Practices

### For Prompts
✅ **DO:**
- Test changes on 5-10 products first
- Be specific ("Include material composition" vs "Better")
- Keep JSON format requirements

❌ **DON'T:**
- Remove placeholder variables like `{product_info}`
- Change without backup (use Git!)
- Make multiple big changes at once

### For Golden Examples
✅ **DO:**
- Choose quality score ≥ 0.8
- Pick varied products (different sizes/colors)
- Update as you approve better products

❌ **DON'T:**
- Mark everything as golden (defeats the purpose)
- Use products with placeholder text ("TODO", "N/A")
- Forget to save after selection

### For Review
✅ **DO:**
- Review lowest quality first (sort by quality)
- Approve generously (≥0.7 is usually good)
- Use feedback for regeneration

❌ **DON'T:**
- Reject without trying regeneration
- Approve products with errors/placeholders
- Give vague feedback ("make it better")

---

## 🔧 Troubleshooting

### "No products found"
**Problem:** You haven't run Step 4 yet  
**Solution:** Run Step 4 first to generate products

### "Prompts not saving"
**Problem:** File permissions or syntax error  
**Solution:** Check `scripts/ai_config.py` is not read-only

### "Regeneration timeout"
**Problem:** Taking too long (>120 seconds)  
**Solution:** Wait and try again, or check API key

### "Quality scores all 0.0"
**Problem:** Cache not built yet  
**Solution:** Run Step 4 (scores calculate automatically)

---

## 📊 Typical Workflow

### Initial Setup (First Time)
1. Run full pipeline (Step 1 → Step 4)
2. Go to **Review AI Outputs**
3. Sort by quality (lowest first)
4. Review and approve best 20-30 products
5. Go to **Golden Examples**
6. Mark top 1-2 per category as golden
7. Done! System is now trained

### Ongoing Maintenance
1. Upload new products
2. Run Step 4 (uses golden examples automatically)
3. Review new products
4. Approve good ones
5. Regenerate bad ones with feedback
6. Update golden examples quarterly

### Improving AI Quality
1. Collect feedback from users
2. Edit prompts based on feedback
3. Test on 10 products
4. Review results
5. If good → apply to all
6. If bad → revert and try different approach

---

## 💡 Tips & Tricks

### Finding Best Products
```
Filter: Quality ≥ 0.8, Approval = Godkendt
→ These are your stars, mark as golden!
```

### Quick Regeneration
```bash
# Command line (faster for bulk)
python scripts/regenerate_product.py "E146223 - Deaktiveret" --feedback "More technical"
```

### Backup Before Changes
```bash
# Save current prompts
git add scripts/ai_config.py
git commit -m "Backup before prompt changes"
```

### Quality Shortcuts
- **1.0** = Perfect (all fields optimal)
- **0.8-0.9** = Very good (minor issues)
- **0.7-0.8** = Good (usable but not ideal)
- **<0.7** = Needs work

---

## 📚 Learn More

- **Full Guide:** [AI_MANAGEMENT_GUIDE.md](AI_MANAGEMENT_GUIDE.md)
- **Technical Details:** [AI_MANAGEMENT_IMPLEMENTATION.md](AI_MANAGEMENT_IMPLEMENTATION.md)
- **Code Flow:** [CODE_FLOW.md](CODE_FLOW.md)

---

## 🆘 Support

**Common Issues:**
- Check logs in **📋 Logs** tab
- See error messages (red boxes)
- Try page refresh (browser F5)

**Still stuck?**
- Check documentation files
- Review pipeline status in **⚙️ Status** tab
- Verify API key is set

---

**Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Ready to use!** 🎉
