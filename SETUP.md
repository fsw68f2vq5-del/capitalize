# SETUP - 2 Steps Only

## What You're Setting Up

A web app that searches 25+ million geographic names in real-time.

---

## STEP 1: Download Database (One-Time, 5-10 minutes)

**Run this command:**

```bash
python geonames_downloader.py
```

**What it does:**
- Downloads 25+ million place names from GeoNames.org
- Creates `geonames.db` file (300MB-1.4GB)
- Only needs to be done ONCE

**Time:** 5-10 minutes depending on internet speed

**Note:** You can choose specific countries or download everything:
- Default: Downloads US, GB, CA, AU (faster)
- For all countries: Edit the file and change line 144

---

## STEP 2: Start the App

### Windows:
**Double-click:** `start.bat`

### Mac/Linux:
**Run:** `./start.sh`

Or just type: `python app.py`

---

## That's It!

After starting, your browser will show:
```
Open http://localhost:5000
```

Go to that address and use the app.

---

## How It Works

1. Type text in the web interface
2. Click "Check Capitalization"
3. App sends request to server
4. Server searches the 25M+ name database
5. Returns correct capitalizations

**Example:**
```
Input:  white clay creek and brandywine river
Server: [Searches database for "white clay creek"]
Server: [Searches database for "brandywine river"]
Output: White Clay Creek and Brandywine River
```

---

## Files Explained

- `geonames_downloader.py` - Downloads the database (run once)
- `app.py` - The web server
- `start.bat` - Windows startup script (double-click)
- `start.sh` - Mac/Linux startup script (./start.sh)
- `geonames.db` - Database file (created by downloader)

---

## Troubleshooting

### "Database not found"
**Solution:** Run `python geonames_downloader.py` first

### "Flask not installed"
**Solution:** The start scripts install it automatically, or run `pip install flask`

### "Python not found"
**Solution:** Install Python from python.org

### Port 5000 already in use
**Solution:** Edit app.py and change the port number at the bottom

### Name not found in results
**Possible reasons:**
- Very obscure location
- Misspelled
- Need to download more countries

---

## Stop the Server

Press `Ctrl+C` in the terminal window

---

## First Time Setup Checklist

- [ ] Run `python geonames_downloader.py` (5-10 min, one time)
- [ ] Wait for download to complete
- [ ] Run `start.bat` (Windows) or `./start.sh` (Mac/Linux)
- [ ] Open http://localhost:5000 in browser
- [ ] Test with your text

---

## Daily Use

After setup, just:
1. Double-click `start.bat` or run `./start.sh`
2. Open http://localhost:5000
3. Use the app

The database stays on your computer, so steps only take seconds after initial setup.

---

## Need Help?

- Read `INTEGRATION.md` for detailed docs
- Run `python examples.py` to see code examples
- Check `START_HERE.md` for full guide
