from flask import Flask, request, jsonify, send_from_directory
import requests
import re
from bs4 import BeautifulSoup
import time
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
load_dotenv()  # Load variables from .env file

app = Flask(__name__, static_folder='.')

# Google Places API Key - use environment variable, fallback to hardcoded
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# Get SendGrid API key from environment variable — NEVER hardcode it!
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
if not SENDGRID_API_KEY:
    print("⚠️ WARNING: SENDGRID_API_KEY not set. Email sending will be simulated.")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/find-email', methods=['POST', 'OPTIONS'])
def find_email():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        location = data.get('location', '')
        office_name = data.get('office_name', '')
        
        if not location or not office_name:
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
        
        email = None
        if website:
            try:
                print(f"Attempting to scrape website: {website}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                website_response = requests.get(website, headers=headers, timeout=15)
                website_content = website_response.text
                print(f"Successfully fetched website, content length: {len(website_content)}")
                
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, website_content)
                print(f"Found {len(emails)} email addresses on website")
                
                skip_domains = ['google.com', 'facebook.com', 'yelp.com', 'healthgrades.com', 'gmail.com', 'yahoo.com']
                valid_emails = [e for e in emails if not any(domain in e.lower() for domain in skip_domains)]
                print(f"After filtering: {len(valid_emails)} valid emails")
                
                mailto_pattern = r'href\s*=\s*["\']mailto:([^"\']+)["\']'
                mailto_emails = re.findall(mailto_pattern, website_content)
                print(f"Found {len(mailto_emails)} mailto links")
                valid_emails.extend([e for e in mailto_emails if not any(domain in e.lower() for domain in ['google.com', 'facebook.com'])])
                
                valid_emails = list(set(valid_emails))
                print(f"Total unique emails: {valid_emails}")
                
                if valid_emails:
                    email = valid_emails[0]
                    specific_emails = [e for e in valid_emails if any(p in e.lower() for p in ['contact', 'info', 'hello', 'office', 'admin'])]
                    if specific_emails:
                        email = specific_emails[0]
                        print(f"Selected specific email: {email}")
                    else:
                        print(f"Using first email found: {email}")
                        
            except Exception as e:
                print(f"Error scraping {website}: {str(e)}")
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
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while searching"}), 500

@app.route('/api/send-email', methods=['POST', 'OPTIONS'])
def send_email():
    # Handle CORS preflight
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
        
        # 🔐 Use SendGrid if key is available
        if SENDGRID_API_KEY:
            # ⚠️ Replace 'no-reply@yourdomain.com' with a verified sender in SendGrid
            from_email = "team.pdi@outlook.com"  # MUST be verified in SendGrid
            
            email_content = f"""
            <p><strong>From:</strong> {user_name} ({user_email})</p>
            <p><strong>Message:</strong></p>
            <p>{message}</p>
            <hr>
            <p><em>Sent via Dental Office Finder</em></p>
            """
            
            mail = Mail(
                from_email=from_email,
                to_emails=office_email,
                subject=subject,
                html_content=email_content
            )
            
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(mail)
            print(f"✅ Real email sent via SendGrid! Status: {response.status_code}")
            return jsonify({"success": True, "message": "Email sent successfully!"})
        else:
            # 🧪 Simulate email sending (for testing without API key)
            print(f"📧 SIMULATED EMAIL:")
            print(f"  To: {office_email}")
            print(f"  From: {user_email}")
            print(f"  Subject: {subject}")
            print(f"  Message: {message}")
            return jsonify({"success": True, "message": "Email sent successfully! (simulated)"})
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
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
