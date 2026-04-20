#!/bin/bash

# Auto-Sec-Blogger cron job with virtual environment
cd /Users/rebugui/.openclaw/workspace/skills/auto-sec-blogger/scripts
source venv/bin/activate
python3 intelligence_pipeline.py --max-articles 5
python3 auto_publish_approved.py >> /tmp/auto-sec-blogger.log 2>&1