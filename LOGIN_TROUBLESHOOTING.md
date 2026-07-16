# Instagram Login Troubleshooting Guide

## Quick Test

Run the test script to debug login issues:

```bash
python test_login.py
```

This will:
- Test login with your credentials
- Save screenshots if errors occur
- Keep the browser open so you can see what's happening
- Provide detailed error messages

## Common Login Issues & Solutions

### 1. "Could not find username field"

**Symptoms:**
- Error: "Could not find username field"
- Screenshot: `login_error_username_field.png`

**Solutions:**
- Instagram may have changed their UI
- Check if you can manually access https://www.instagram.com/accounts/login/
- Try increasing `slow_mode` in config.yaml
- Make sure ChromeDriver is up to date
- Instagram may be blocking automated access

### 2. "Invalid credentials" or "Password incorrect"

**Symptoms:**
- Error: "Login failed: Detected error message containing 'incorrect'"
- Screenshot: `login_error_detected.png`

**Solutions:**
1. **Verify your credentials:**
   - Check `.env` file has correct username and password
   - Make sure there are no extra spaces
   - Try logging in manually on Instagram website first

2. **Check for typos:**
   ```bash
   # In PowerShell, check your .env file
   type .env
   ```

3. **Account may be locked:**
   - Instagram may have temporarily locked your account
   - Wait 24 hours and try again
   - Check your email for Instagram security notifications

### 3. "Security Challenge" or "Verify Your Identity"

**Symptoms:**
- Warning: "Security challenge detected"
- Screenshot: `login_security_challenge.png`
- Instagram asks for phone verification or email code

**Solutions:**
1. **Complete the challenge manually:**
   - The browser will stay open
   - Complete the verification in the browser window
   - The script will wait 10 seconds for you

2. **Disable 2FA temporarily** (for testing only):
   - Go to Instagram Settings > Security > Two-Factor Authentication
   - Temporarily disable it
   - Re-enable after testing

3. **Use cookie-based login** (see below)

### 4. "Please wait a few minutes"

**Symptoms:**
- Error: "Please wait a few minutes before you try again"
- Instagram rate limiting

**Solutions:**
1. **Wait 1-2 hours** before trying again
2. **Use a different IP address** (VPN)
3. **Reduce scraping frequency**
4. **Increase `slow_mode`** in config.yaml to 5-10 seconds

### 5. Login appears successful but script says it failed

**Symptoms:**
- You can see you're logged in the browser
- But script reports login failed

**Solutions:**
1. **Check the current URL** in the logs
2. **Instagram may have redirected** to a different page
3. **The script may need updated selectors** - check `login_page_source.html`
4. **Try running in non-headless mode** to see what's happening

## Advanced: Cookie-Based Login

If username/password login keeps failing, use cookies:

### Step 1: Export Cookies Manually

1. **Log into Instagram manually** in Chrome
2. **Install a cookie extension** like "Cookie-Editor" or "EditThisCookie"
3. **Export cookies** as JSON
4. **Save as** `instagram_cookies.json` in project root

### Step 2: Add Cookie Loading Function

Add this to `utils.py`:

```python
def load_instagram_cookies(driver, cookie_file='instagram_cookies.json'):
    """Load cookies from JSON file."""
    import json
    try:
        driver.get("https://www.instagram.com/")
        time.sleep(2)
        
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
            
        for cookie in cookies:
            # Remove fields that Selenium doesn't accept
            cookie.pop('sameSite', None)
            cookie.pop('storeId', None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"Could not add cookie: {e}")
        
        driver.refresh()
        time.sleep(3)
        logger.info("Cookies loaded successfully")
        return True
    except FileNotFoundError:
        logger.error(f"Cookie file not found: {cookie_file}")
        return False
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return False
```

### Step 3: Modify scraper.py

In `scraper.py`, replace the login call:

```python
# Instead of:
# if not instagram_login(driver, username, password, slow_mode=slow_mode):

# Use:
from utils import load_instagram_cookies
if not load_instagram_cookies(driver, 'instagram_cookies.json'):
    logger.error("Failed to load cookies. Exiting.")
    return
```

## Debugging Steps

1. **Run test script:**
   ```bash
   python test_login.py
   ```

2. **Check screenshots:**
   - Look at any `login_error_*.png` files generated
   - See what Instagram is showing

3. **Check page source:**
   - Open `login_page_source.html` in a browser
   - Search for error messages
   - Check the HTML structure

4. **Check logs:**
   - Look at `instagram_scraper.log`
   - Find the exact error message
   - Check which selector worked/failed

5. **Manual verification:**
   - Try logging in manually at https://www.instagram.com/accounts/login/
   - If manual login fails, it's an account issue, not a code issue

## Prevention Tips

1. **Use slow_mode:** Set to 3-5 seconds in config.yaml
2. **Don't run too frequently:** Wait between runs
3. **Use real browser profile:** Consider using a persistent Chrome profile
4. **Respect rate limits:** Instagram will block aggressive automation
5. **Keep ChromeDriver updated:** Match your Chrome version

## Still Having Issues?

1. Check Instagram's status: https://www.instagram.com
2. Verify your account isn't suspended
3. Try from a different network/IP
4. Consider using Instagram's official API (requires approval)
5. Check if Instagram has updated their login page structure

