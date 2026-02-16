# Analytics Setup Instructions

## Option 1: GoatCounter (Recommended - Privacy-Friendly)

GoatCounter is free, lightweight, and privacy-friendly. It doesn't use cookies and is GDPR compliant.

### Setup Steps:

1. **Sign up at https://www.goatcounter.com/**
   - Click "Sign up"
   - Choose a code: e.g., `ado1stat` (your site will be at `ado1stat.goatcounter.com`)
   - Enter your email
   - Verify email and set password

2. **Update index.html**
   - Open `index.html`
   - Find **two places** with `YOUR-CODE` near the bottom
   - Replace `YOUR-CODE` with your chosen code (e.g., `ado1stat`)

   Example:
   ```html
   <!-- Before -->
   <script data-goatcounter="https://YOUR-CODE.goatcounter.com/count"

   <!-- After -->
   <script data-goatcounter="https://ado1stat.goatcounter.com/count"
   ```

3. **Enable public statistics (optional)**
   - Log in to GoatCounter dashboard
   - Go to Settings → Public
   - Enable "Make statistics public"
   - This allows showing visitor counts on your website

4. **Commit and push changes**
   ```bash
   git add index.html ANALYTICS_SETUP.md
   git commit -m "Add visitor counter with GoatCounter"
   git push origin main
   ```

5. **View your stats**
   - Dashboard: https://YOUR-CODE.goatcounter.com/
   - Public stats: https://YOUR-CODE.goatcounter.com/stats (if enabled)

### What You Get:

- ✅ Unique visitors today
- ✅ Total unique visitors
- ✅ Page views per day
- ✅ Referrers (where visitors come from)
- ✅ Browser/OS stats
- ✅ Privacy-friendly (no cookies)
- ✅ Free for non-commercial use

---

## Option 2: Google Analytics (More Features)

If you want more detailed analytics, use Google Analytics.

### Setup Steps:

1. **Create Google Analytics account**
   - Go to https://analytics.google.com/
   - Click "Start measuring"
   - Create account and property
   - Get your Measurement ID (looks like: `G-XXXXXXXXXX`)

2. **Add to index.html**

   Add this before `</head>`:
   ```html
   <!-- Google Analytics -->
   <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
   <script>
     window.dataLayer = window.dataLayer || [];
     function gtag(){dataLayer.push(arguments);}
     gtag('js', new Date());
     gtag('config', 'G-XXXXXXXXXX');
   </script>
   ```

3. **Note**: Google Analytics doesn't show visitor count on the page itself - only in the dashboard

---

## Comparison

| Feature | GoatCounter | Google Analytics |
|---------|------------|------------------|
| **Privacy** | ✅ Excellent | ⚠️ Tracks users |
| **Show count on page** | ✅ Yes | ❌ No |
| **Free** | ✅ Yes | ✅ Yes |
| **Real-time stats** | ✅ Yes | ✅ Yes |
| **Detailed analytics** | ⚠️ Basic | ✅ Advanced |
| **Setup difficulty** | ✅ Easy | ⚠️ Medium |
| **GDPR compliant** | ✅ Yes | ⚠️ Requires consent |

**Recommendation**: Use GoatCounter for this project since you want to display visitor counts on the page and it's privacy-friendly.
