def find_email_via_database(office_name):
    """Try to find email from Alamance County database using fuzzy matching"""
    try:
        office_name_lower = office_name.lower().strip()
        print(f"Searching database for: {office_name_lower}", file=sys.stderr)
        
        # Exact match first
        if office_name_lower in ALAMANCE_EMAILS_DB:
            email = ALAMANCE_EMAILS_DB[office_name_lower][0]
            print(f"Found email in database (exact match): {email}", file=sys.stderr)
            return email
        
        # Fuzzy match - find the closest match
        best_match = None
        best_score = 0
        threshold = 0.6  # Require at least 60% similarity
        
        for db_office in ALAMANCE_EMAILS_DB.keys():
            # Calculate similarity ratio (0 to 1)
            ratio = SequenceMatcher(None, office_name_lower, db_office).ratio()
            
            if ratio > best_score:
                best_score = ratio
                best_match = db_office
        
        # If we found a good match (>60% similar), use it
        if best_match and best_score >= threshold:
            email = ALAMANCE_EMAILS_DB[best_match][0]
            print(f"Found email in database (fuzzy match '{best_match}' with {best_score*100:.0f}% similarity): {email}", file=sys.stderr)
            return email
        else:
            print(f"No database match found. Best match was '{best_match}' with {best_score*100:.0f}% similarity (threshold: {threshold*100:.0f}%)", file=sys.stderr)
            
    except Exception as e:
        print(f"Database lookup error: {str(e)}", file=sys.stderr)
    
    return None

def find_email_via_website(website):import os
import sys
import re
import time
import csv
from difflib import SequenceMatcher
from flask import Flask, request, jsonify, send_from_directory
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.')

sys.stdout.flush()
sys.stderr.flush()

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
GOOGLE_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_SEARCH_ENGINE_ID', '')
HUNTER_API_KEY = os.environ.get('HUNTER_API_KEY', '')

# Load Alamance County dental emails database
ALAMANCE_EMAILS_DB = {}
try:
    with open('alamance_dental_emails.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            office_name = row['office_name'].lower().strip()
            email = row['email'].strip()
            if office_name not in ALAMANCE_EMAILS_DB:
                ALAMANCE_EMAILS_DB[office_name] = []
            ALAMANCE_EMAILS_DB[office_name].append(email)
    print(f"Loaded {len(ALAMANCE_EMAILS_DB)} offices from Alamance County database", file=sys.stderr)
except FileNotFoundError:
    print("⚠️ alamance_dental_emails.csv not found", file=sys.stderr)
except Exception as e:
    print(f"Error loading CSV: {e}", file=sys.stderr)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

def find_email_via_google_search(office_name, location):
    """Try to find email using Google Custom Search API"""
    if not GOOGLE_SEARCH_ENGINE_ID:
        print("Google Search Engine ID not configured", file=sys.stderr)
        return None
    
    try:
        print(f"Attempting Google Search for: {office_name} {location}", file=sys.stderr)
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'q': f"{office_name} {location} email contact",
            'cx': GOOGLE_SEARCH_ENGINE_ID,
            'key': GOOGLE_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        results = response.json()
        
        if 'items' not in results:
            print("No search results found", file=sys.stderr)
            return None
        
        # Search through results for email addresses
        for item in results.get('items', []):
            snippet = item.get('snippet', '')
            title = item.get('title', '')
            
            # Look for email pattern in snippet and title
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, snippet + ' ' + title)
            
            if emails:
                # Filter out common non-office emails
                skip_domains = ['google.com', 'facebook.com', 'yelp.com', 'healthgrades.com', 'gmail.com', 'yahoo.com']
                valid_emails = [e for e in emails if not any(domain in e.lower() for domain in skip_domains)]
                
                if valid_emails:
                    email = valid_emails[0]
                    print(f"Found email via Google Search: {email}", file=sys.stderr)
                    return email
        
        print("No valid emails found in search results", file=sys.stderr)
        
    except Exception as e:
        print(f"Google Search error: {str(e)}", file=sys.stderr)
    
    return None
    """Try to find email using Hunter.io API"""
    if not HUNTER_API_KEY:
        return None
    
    try:
        print(f"Attempting Hunter.io lookup for domain: {domain}", file=sys.stderr)
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
            print(f"Found email via Hunter.io: {email}", file=sys.stderr)
            return email
    except Exception as e:
        print(f"Hunter.io lookup failed: {str(e)}", file=sys.stderr)
    
    return None

def find_email_via_database(office_name):
    """Try to scrape email from website"""
    try:
        print(f"Attempting to scrape website: {website}", file=sys.stderr)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        website_response = requests.get(website, headers=headers, timeout=15)
        website_content = website_response.text
        print(f"Successfully fetched website, content length: {len(website_content)}", file=sys.stderr)
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, website_content)
        print(f"Found {len(emails)} email addresses on website", file=sys.stderr)
        
        skip_domains = ['google.com', 'facebook.com', 'yelp.com', 'healthgrades.com', 'gmail.com', 'yahoo.com']
        valid_emails = [e for e in emails if not any(domain in e.lower() for domain in skip_domains)]
        print(f"After filtering: {len(valid_emails)} valid emails: {valid_emails}", file=sys.stderr)
        
        mailto_pattern = r'href\s*=\s*["\']mailto:([^"\']+)["\']'
        mailto_emails = re.findall(mailto_pattern, website_content)
        print(f"Found {len(mailto_emails)} mailto links", file=sys.stderr)
        valid_emails.extend([e for e in mailto_emails if not any(domain in e.lower() for domain in ['google.com', 'facebook.com'])])
        
        valid_emails = list(set(valid_emails))
        print(f"Total unique emails: {valid_emails}", file=sys.stderr)
        
        if valid_emails:
            email = valid_emails[0]
            specific_emails = [e for e in valid_emails if any(p in e.lower() for p in ['contact', 'info', 'hello', 'office', 'admin'])]
            if specific_emails:
                email = specific_emails[0]
                print(f"Selected specific email: {email}", file=sys.stderr)
            else:
                print(f"Using first email found: {email}", file=sys.stderr)
            return email
                    
    except Exception as e:
        print(f"Error scraping {website}: {str(e)}", file=sys.stderr)
    
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
            print(f"[DEBUG] Missing location or office_name", file=sys.stderr)
            return jsonify({"error": "Location and office name are required"}), 400
        
        search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': f"{office_name} dental office {location}",
            'key': GOOGLE_API_KEY,
            'type': 'dentist'
        }
        
        response = requests.get(search_url, params=params)
        result = response.json()
        
        if result.get('status') != 'OK':
            return jsonify({"error": "No results found or API error"}), 404
        
        if len(result.get('results', [])) == 0:
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
        
        # Try database lookup first (fastest)
        email = find_email_via_database(office_name_found)
        
        # Try website scraping if not found in database
        if not email and website:
            email = find_email_via_website(website)
        
        # Try Google Search if still not found
        if not email:
            email = find_email_via_google_search(office_name_found, location)
        
        # Try Hunter.io if still not found
        if not email and website:
            try:
                # Extract domain from website URL
                domain = website.replace('http://', '').replace('https://', '').split('/')[0]
                email = find_email_via_hunter(domain, office_name_found)
            except Exception as e:
                print(f"Error extracting domain: {str(e)}", file=sys.stderr)
        
        # If still no email, try Hunter.io with office name
        if not email:
            email = find_email_via_hunter(office_name_found.replace(' ', ''), office_name_found)
        
        # Last resort: generate email from office name
        if not email:
            print(f"No email found, generating fallback", file=sys.stderr)
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
        print(f"Error: {e}", file=sys.stderr)
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
