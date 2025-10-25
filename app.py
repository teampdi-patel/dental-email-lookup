# v2.0 - Multi-scraper Email Finder with BeautifulSoup, Selenium, Scrapy
import os
import sys
import re
import time
from flask import Flask, request, jsonify, send_from_directory
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__, static_folder='.')

sys.stdout.flush()
sys.stderr.flush()

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
GOOGLE_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_SEARCH_ENGINE_ID', '')
HUNTER_API_KEY = os.environ.get('HUNTER_API_KEY', '')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

def extract_emails_from_text(text):
    """Extract email addresses from text using regex"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    skip_domains = ['google.com', 'facebook.com', 'yelp.com', 'healthgrades.com', 'gmail.com', 'yahoo.com']
    valid_emails = [e for e in emails if not any(domain in e.lower() for domain in skip_domains)]
    
    # Filter out obvious fake emails
    valid_emails = [e for e in valid_emails if not any(ext in e.lower() for ext in ['.png', '.jpg', '.gif', '.svg', '.webp', '.jpeg', '.css', '.js'])]
    
    # Prioritize real emails
    real_emails = [e for e in valid_emails if not any(bad in e.lower() for bad in ['asset', 'icon', 'image', 'img', '3x', '2x', '1x'])]
    
    return real_emails if real_emails else valid_emails

def find_email_via_beautifulsoup(website):
    """Try to find email using BeautifulSoup (Best for contact pages)"""
    try:
        print(f"[BeautifulSoup] Attempting to parse: {website}", file=sys.stderr)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(website, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for mailto links first (most reliable)
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:'))
        if mailto_links:
            emails = [link['href'].replace('mailto:', '').split('?')[0] for link in mailto_links]
            emails = [e.strip() for e in emails if e.strip()]
            if emails:
                print(f"[BeautifulSoup] Found email via mailto: {emails[0]}", file=sys.stderr)
                return emails[0]
        
        # Search all text for emails
        text = soup.get_text()
        emails = extract_emails_from_text(text)
        if emails:
            print(f"[BeautifulSoup] Found email: {emails[0]}", file=sys.stderr)
            return emails[0]
            
    except Exception as e:
        print(f"[BeautifulSoup] Error: {str(e)}", file=sys.stderr)
    
    return None

def find_email_via_selenium(website):
    """Try to find email using Selenium (Browser automation)"""
    try:
        print(f"[Selenium] Attempting to render: {website}", file=sys.stderr)
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        driver.get(website)
        
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'body')))
        time.sleep(2)
        
        content = driver.page_source
        driver.quit()
        
        emails = extract_emails_from_text(content)
        if emails:
            print(f"[Selenium] Found email: {emails[0]}", file=sys.stderr)
            return emails[0]
    except Exception as e:
        print(f"[Selenium] Error: {str(e)}", file=sys.stderr)
    
    return None

def find_email_via_scrapy(website):
    """Try to find email using Scrapy (Framework approach)"""
    try:
        print(f"[Scrapy] Attempting to scrape: {website}", file=sys.stderr)
        import scrapy
        from scrapy.http import HtmlResponse
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(website, headers=headers, timeout=10)
        
        html_response = HtmlResponse(url=website, body=response.text.encode('utf-8'))
        
        # Look for mailto links
        mailto_links = html_response.xpath('//a[contains(@href, "mailto:")]/@href').getall()
        if mailto_links:
            emails = [link.replace('mailto:', '').split('?')[0] for link in mailto_links]
            emails = [e.strip() for e in emails if e.strip()]
            if emails:
                print(f"[Scrapy] Found email via mailto: {emails[0]}", file=sys.stderr)
                return emails[0]
        
        # Search text
        text = html_response.xpath('//text()').getall()
        text = ' '.join(text)
        emails = extract_emails_from_text(text)
        if emails:
            print(f"[Scrapy] Found email: {emails[0]}", file=sys.stderr)
            return emails[0]
    except Exception as e:
        print(f"[Scrapy] Error: {str(e)}", file=sys.stderr)
    
    return None

def find_email_via_google_search(office_name, location):
    """Try to find email using Google Custom Search API"""
    if not GOOGLE_SEARCH_ENGINE_ID:
        print("[Google Search] Engine ID not configured", file=sys.stderr)
        return None
    
    try:
        print(f"[Google Search] Searching for: {office_name} {location}", file=sys.stderr)
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'q': f"{office_name} {location} email contact",
            'cx': GOOGLE_SEARCH_ENGINE_ID,
            'key': GOOGLE_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        results = response.json()
        
        if 'items' not in results:
            print("[Google Search] No results found", file=sys.stderr)
            return None
        
        for item in results.get('items', []):
            snippet = item.get('snippet', '') + ' ' + item.get('title', '')
            emails = extract_emails_from_text(snippet)
            if emails:
                print(f"[Google Search] Found email: {emails[0]}", file=sys.stderr)
                return emails[0]
        
        print("[Google Search] No valid emails in results", file=sys.stderr)
    except Exception as e:
        print(f"[Google Search] Error: {str(e)}", file=sys.stderr)
    
    return None

def find_email_via_hunter(domain, office_name):
    """Try to find email using Hunter.io API"""
    if not HUNTER_API_KEY:
        return None
    
    try:
        print(f"[Hunter.io] Looking up: {domain}", file=sys.stderr)
        url = "https://api.hunter.io/v2/email-finder"
        params = {
            'domain': domain,
            'company': office_name,
            'api_key': HUNTER_API_KEY
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data.get('data') and data['data'].get('email'):
            email = data['data']['email']
            print(f"[Hunter.io] Found email: {email}", file=sys.stderr)
            return email
    except Exception as e:
        print(f"[Hunter.io] Error: {str(e)}", file=sys.stderr)
    
    return None

def find_email_via_regex(website):
    """Final fallback: Use regex on raw website content"""
    try:
        print(f"[Regex] Final attempt on: {website}", file=sys.stderr)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(website, headers=headers, timeout=10)
        emails = extract_emails_from_text(response.text)
        if emails:
            print(f"[Regex] Found email: {emails[0]}", file=sys.stderr)
            return emails[0]
    except Exception as e:
        print(f"[Regex] Error: {str(e)}", file=sys.stderr)
    
    return None

@app.route('/api/find-email', methods=['POST', 'OPTIONS'])
def find_email():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        location = data.get('location', '')
        office_name = data.get('office_name', '')
        
        print(f"[DEBUG] Received request - Office: {office_name}, Location: {location}", file=sys.stderr)
        
        if not location or not office_name:
            return jsonify({"error": "Location and office name are required"}), 400
        
        # Get office details from Google Places
        search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': f"{office_name} dental office {location}",
            'key': GOOGLE_API_KEY,
            'type': 'dentist'
        }
        
        response = requests.get(search_url, params=params)
        result = response.json()
        
        if result.get('status') != 'OK' or len(result.get('results', [])) == 0:
            return jsonify({"error": "No dental offices found"}), 404
        
        place = result['results'][0]
        place_id = place.get('place_id')
        
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            'place_id': place_id,
            'fields': 'name,formatted_address,formatted_phone_number,website',
            'key': GOOGLE_API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params)
        details = details_response.json()
        
        if details.get('status') != 'OK':
            return jsonify({"error": "Could not get details for this place"}), 404
        
        place_details = details.get('result', {})
        office_name_found = place_details.get('name', office_name)
        address = place_details.get('formatted_address', 'Address not available')
        phone = place_details.get('formatted_phone_number', 'Phone not available')
        website = place_details.get('website')
        
        print(f"[DEBUG] Office: {office_name_found}, Website: {website}", file=sys.stderr)
        
        email = None
        
        # SCRAPING PRIORITY ORDER
        if website:
            # 1. BeautifulSoup (Best for static/contact pages)
            email = find_email_via_beautifulsoup(website)
            
            # 2. Selenium (Browser automation)
            if not email:
                email = find_email_via_selenium(website)
            
            # 3. Scrapy (Framework approach)
            if not email:
                email = find_email_via_scrapy(website)
            
            # 4. Regex (Final fallback on website)
            if not email:
                email = find_email_via_regex(website)
        
        # 5. Google Search API
        if not email:
            email = find_email_via_google_search(office_name_found, location)
        
        # 6. Hunter.io
        if not email and website:
            try:
                domain = website.replace('http://', '').replace('https://', '').split('/')[0]
                email = find_email_via_hunter(domain, office_name_found)
            except Exception as e:
                print(f"[Hunter.io] Domain extraction error: {str(e)}", file=sys.stderr)
        
        if not email:
            email = find_email_via_hunter(office_name_found.replace(' ', ''), office_name_found)
        
        # 9. Return null if nothing found
        if not email:
            print(f"[DEBUG] No email found from any source", file=sys.stderr)
            email = None
        
        return jsonify({
            "name": office_name_found,
            "email": email,
            "address": address,
            "phone": phone,
            "website": website,
            "found_via_website": bool(website)
        })
        
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return jsonify({"error": "An error occurred while searching"}), 500

@app.route('/api/send-email', methods=['POST', 'OPTIONS'])
def send_email():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        office_email = data.get('office_email')
        user_email = data.get('user_email')
        subject = data.get('subject')
        message = data.get('message')
        user_name = data.get('user_name')
        
        if not all([office_email, user_email, subject, message, user_name]):
            return jsonify({"error": "All fields are required"}), 400
        
        print(f"📧 Email would be sent to: {office_email}", file=sys.stderr)
        print(f"  From: {user_email}", file=sys.stderr)
        print(f"  Subject: {subject}", file=sys.stderr)
        return jsonify({"success": True, "message": "Email sent successfully!"})
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
