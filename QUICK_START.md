# Quick Start Guide

## ✅ Login is Working!

Great! Your login is now working. Here's how to run the complete scraper:

## Running the Full Scraper

1. **Make sure your `.env` file is set up:**
   ```
   INSTAGRAM_USERNAME=your_username
   INSTAGRAM_PASSWORD=your_password
   ```

2. **Check your `config.yaml` settings:**
   - `keyword`: The hashtag/keyword to search (default: "lifestyle")
   - `num_posts`: Number of posts to process (start with 5-10 for testing)
   - `min_comments`: Minimum comments required (default: 50)
   - `browser.headless`: Set to `false` to see what's happening
   - `browser.slow_mode`: Delay in seconds (2-5 recommended)

3. **Run the scraper:**
   ```bash
   cd instagram-engagement
   python scraper.py
   ```

## What the Scraper Does

1. ✅ **Logs into Instagram** (you've confirmed this works!)
2. 🔍 **Searches for keyword** - Navigates to hashtag page
3. 📋 **Collects post URLs** - Scrolls and collects unique post links
4. 💬 **Extracts comments** - Opens each post and collects all comments
5. 🏷️ **Classifies comments** - Categorizes as text/emoji/mixed
6. 📊 **Calculates metrics** - Determines Pass/Fail based on engagement
7. 💾 **Saves to CSV** - Outputs results to `output/results.csv`

## Improvements Made

### 1. Enhanced Search Function
- Direct navigation to hashtag pages (more reliable)
- Multiple selector fallbacks for finding posts
- Better scrolling logic with progress tracking
- URL deduplication and cleaning

### 2. Improved Comment Extraction
- Multiple selectors for finding comments
- Better filtering of non-comment text
- Duplicate detection (case-insensitive)
- Automatic "Load more comments" button clicking
- Progress logging every 5 scroll attempts

### 3. Better Creator Handle Extraction
- Multiple selector strategies
- Fallback to URL parsing
- Validation to ensure valid handles

### 4. Enhanced Error Handling
- More detailed logging at each step
- Better error messages
- Graceful handling of missing elements

## Expected Output

The CSV file will contain:
- `creator_handle`: Instagram username
- `post_url`: Full post URL
- `total_comments`: Number of comments extracted
- `text_percentage`: % of text-only comments
- `emoji_percentage`: % of emoji-only comments
- `mixed_percentage`: % of mixed comments
- `result`: "Pass" or "Fail"

## Tips for Best Results

1. **Start Small**: Set `num_posts: 5` in config.yaml for testing
2. **Use Slow Mode**: Set `slow_mode: 3-5` to avoid rate limits
3. **Monitor Logs**: Watch `instagram_scraper.log` for detailed progress
4. **Check Browser**: Run with `headless: false` first to see what's happening
5. **Be Patient**: Comment extraction can take time for posts with many comments

## Troubleshooting

### No Posts Found
- Check if the keyword/hashtag exists
- Try a different, more popular hashtag
- Increase `slow_mode` if Instagram is slow to load

### No Comments Extracted
- Some posts may have comments disabled
- Comments may require login (should be logged in)
- Instagram UI may have changed (check selectors)

### Rate Limiting
- Increase `slow_mode` to 5-10 seconds
- Reduce `num_posts` to process fewer posts
- Wait 1-2 hours between runs

## Next Steps

1. Run with a small number of posts first (5-10)
2. Check the output CSV to verify results
3. Adjust `min_comments` and other settings as needed
4. Scale up to more posts once you're confident it's working

Good luck with your scraping! 🚀

