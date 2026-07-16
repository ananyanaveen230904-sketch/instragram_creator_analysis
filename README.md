# Instagram Engagement Scraper - Phase 2

A Python + Selenium tool that automatically searches Instagram, extracts comments from posts, classifies them, calculates Engagement Quality Scores (EQS), and provides creator-level analytics.

## Project Overview

This tool automates the process of:

### Phase 1: Initial Post Discovery
1. Searching Instagram for a keyword (default: "lifestyle")
2. Collecting post URLs from search/explore results
3. Extracting comments from each post
4. Classifying comments into:
   - **Text comments**: Contains letters/numbers but no emojis
   - **Emoji-only comments**: Contains only emojis
   - **Mixed comments**: Contains both emojis and text
5. Determining whether posts qualify as "high text-based engagement"
   - Must have ≥ minimum required comments (default: 50)
   - At least 50% comments must be text-based

### Phase 2: Creator Analysis
6. For each post that passes Phase-1 criteria:
   - Opens the creator's profile
   - Fetches their latest N posts (default: 5)
   - Runs full analysis on each post (comment extraction + classification + EQS)
7. Calculates Engagement Quality Score (EQS) for every post
8. Generates creator-level summaries
9. Saves results to two CSV files: `posts.csv` and `creators.csv`

## Engagement Quality Score (EQS)

EQS is calculated using the following formula:

```
EQS = (Text% × 0.6) + (Mixed% × 0.3) - (Emoji% × 0.1) + (Unique commenters ratio × 0.2)
```

Where:
- **Text%**: Percentage of text-only comments
- **Mixed%**: Percentage of mixed comments
- **Emoji%**: Percentage of emoji-only comments
- **Unique commenters ratio**: unique_users / total_comments

## Quick Start

```bash
git clone <repo>
cd insta-creators
pip install -r requirements.txt
cd src
python scraper.py
```

## Project Structure

```
insta-creators/
├── src/
│   ├── scraper.py              # Main Phase-2 script
│   ├── comment_classifier.py  # Comment classification logic
│   ├── post_analyzer.py        # Post analysis and EQS calculation
│   ├── creator_analyzer.py    # Creator-level analysis
│   └── utils.py               # Utility functions
├── config/
│   └── config.yaml            # Configuration file
├── output/
│   ├── posts.csv              # Post-level results (generated)
│   └── creators.csv           # Creator-level results (generated)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── .env                       # Environment variables (create this)
```

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install ChromeDriver

The script requires ChromeDriver to be installed and accessible in your PATH.

**Windows:**
- Download ChromeDriver from https://chromedriver.chromium.org/
- Extract and add to PATH, or place in the same directory as the script
- Ensure Chrome browser is installed

**macOS:**
```bash
brew install chromedriver
```

**Linux:**
```bash
sudo apt-get install chromium-chromedriver
```

### 3. Create `.env` File

Create a `.env` file in the project root with your Instagram credentials:

```
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

**⚠️ IMPORTANT:** Never commit the `.env` file to version control!

Alternatively, you can set credentials in `config/config.yaml` under the `login` section.

### 4. Configure Settings

Edit `config/config.yaml` to customize:

```yaml
# Search settings
keyword: "lifestyle"  # Keyword to search on Instagram
number_of_initial_posts_to_scan: 20  # Number of initial posts to scan

# Creator analysis settings
posts_per_creator: 5  # Number of posts to analyze per creator

# Engagement criteria
minimum_comments_required: 50  # Minimum comments required
minimum_text_percentage_required: 50  # Minimum text-based percentage

# Scrolling settings
scroll_delay_range: [2, 4]  # Random delay range in seconds

# Browser settings
browser:
  headless: false  # Run browser in headless mode
  slow_mode: 2  # Additional delay in seconds

# Output paths
output:
  posts_csv: "output/posts.csv"
  creators_csv: "output/creators.csv"
```

## How to Run

1. Ensure all dependencies are installed
2. Create `.env` file with Instagram credentials (or set in config.yaml)
3. Configure `config/config.yaml` if needed
4. Run the script from the `src/` directory:

```bash
cd src
python scraper.py
```

The script will:
- Log into Instagram
- Search for the configured keyword
- Collect initial post URLs (Phase 1)
- Check each post for Phase-1 criteria
- For passing posts, analyze the creator's profile (Phase 2)
- Calculate EQS for each post
- Generate creator-level summaries
- Save results to `posts.csv` and `creators.csv`

Progress will be displayed with progress bars and detailed logging.

## Output CSV Formats

### posts.csv

One row per post with the following columns:

- `creator_handle`: Instagram handle of the post creator
- `post_url`: Full URL of the Instagram post
- `total_comments`: Total number of comments extracted
- `text_percentage`: Percentage of text-only comments
- `emoji_percentage`: Percentage of emoji-only comments
- `mixed_percentage`: Percentage of mixed comments
- `unique_commenters_ratio`: Ratio of unique commenters (unique_users / total_comments)
- `EQS`: Engagement Quality Score
- `pass`: "Pass" or "Fail" based on engagement criteria

### creators.csv

One row per creator with the following columns:

- `creator_handle`: Instagram handle
- `posts_analyzed`: Total number of posts analyzed for this creator
- `posts_passed`: Number of posts that passed the criteria
- `avg_text_percentage`: Average text percentage across all posts
- `avg_emoji_percentage`: Average emoji percentage across all posts
- `avg_mixed_percentage`: Average mixed percentage across all posts
- `avg_EQS`: Average Engagement Quality Score
- `best_EQS`: Highest EQS score among all posts
- `worst_EQS`: Lowest EQS score among all posts

## Logging, Error Handling & Progress Tracking

This project includes comprehensive logging, robust error handling, and real-time progress tracking.

### Logging System

- **Dual Output**: Logs are written to both console and `instagram_scraper.log`
- **Log Format**: Timestamp, log level, and detailed message
- **Comprehensive Coverage**: All operations are logged

### Error Handling

- **Try-Except Blocks**: All critical operations are wrapped
- **Specific Exception Handling**: TimeoutException, NoSuchElementException, etc.
- **Graceful Degradation**: Multiple fallback selectors and alternative methods
- **Error Recovery**: Automatic retries with different selectors
- **Debugging Files**: Screenshots and page source saved on errors

### Progress Tracking

- **Progress Bars**: Visual progress indicators for Phase-1 and Phase-2
- **Progress Logging**: Detailed progress messages
- **Summary Statistics**: Complete summary at the end

## Troubleshooting

### Rate Limits & Blocked Requests

**Solutions:**
1. Increase `slow_mode` in `config.yaml` (e.g., set to 5-10 seconds)
2. Reduce `number_of_initial_posts_to_scan` and `posts_per_creator`
3. Add delays between actions
4. Use a VPN or different IP address
5. Wait 24 hours if temporarily blocked

### Login Issues

**Quick Debug:**
1. Run the test script first:
   ```bash
   python test_login.py
   ```

**Solutions:**
1. Verify credentials in `.env` file or `config.yaml`
2. Check generated files: `login_error_*.png` screenshots
3. Check `login_page_source.html` for error messages
4. Wait before retrying if rate-limited

### Slow Loading / Timeout Errors

**Solutions:**
1. Check internet connection
2. Increase timeout values in the code
3. Reduce number of posts to process
4. Run in non-headless mode to see what's happening
5. Update ChromeDriver to match your Chrome version

## Best Practices

1. **Respect Rate Limits**: Don't scrape too aggressively
2. **Use Delays**: The script includes random delays to appear more human-like
3. **Monitor Logs**: Check `instagram_scraper.log` for detailed operation history
4. **Test Small First**: Start with small numbers to test before larger runs
5. **Keep Updated**: Instagram changes frequently; update selectors as needed
6. **Legal Compliance**: Ensure you comply with Instagram's Terms of Service

## Code Architecture

- **`src/scraper.py`**: Main Phase-2 orchestration script
- **`src/comment_classifier.py`**: Comment classification using regex
- **`src/post_analyzer.py`**: Post analysis and EQS calculation
- **`src/creator_analyzer.py`**: Creator-level analysis and aggregation
- **`src/utils.py`**: Reusable utility functions (config, driver, login, CSV)
- **`config/config.yaml`**: Centralized configuration
- **Modular design**: Easy to extend and maintain

## Dependencies

- **selenium**: Browser automation
- **python-dotenv**: Environment variable management
- **pyyaml**: YAML configuration parsing
- **pandas**: CSV data handling
- **tqdm**: Progress bars

## Notes

- Instagram's UI changes frequently; XPath selectors may need updates
- The script includes anti-detection measures but may still trigger rate limits
- For production use, consider Instagram's official API
- Always respect Instagram's Terms of Service and robots.txt
- Unique commenters ratio is approximated using unique comments (exact username extraction requires additional DOM parsing)

## License

This project is for educational purposes. Use responsibly and in compliance with Instagram's Terms of Service.
