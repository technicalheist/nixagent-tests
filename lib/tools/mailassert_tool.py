import os
import time
import requests
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

def search_emails(payload: Dict[str, Any], max_retries: int = 5, interval: int = 20) -> Dict[str, Any]:
    """
    Search emails using Mailassert API, with retry mechanism.
    
    Args:
        payload (dict): Dictionary with search filters.
            Example:
            {
                "to": "test12@automationtest-mytest.mailassert.com", 
                "subject" :  "Hello"
            }
        max_retries (int): Maximum number of attempts to search for emails.
        interval (int): Delay in seconds between attempts.
            
    Returns:
        dict: The JSON response from the API.
    """
    url = "https://mailassert.com/api/emails/search"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('MAILASSERT_API')}"
    }
    
    for attempt in range(max_retries):
        try:
            # requests.post automatically serializes the dictionary to JSON format
            # when using the `json` parameter.
            response = requests.post(url, headers=headers, json=payload)
            
            # Raise an exception for HTTP errors (4xx or 5xx)
            response.raise_for_status()
            
            # Try to parse and return JSON response
            try:
                data = response.json()
            except ValueError:
                # If response is not JSON, return as text inside a dictionary
                data = {"response_text": response.text}
                
            # If the response contains no emails, wait and retry
            if isinstance(data, dict) and "emails" in data and len(data["emails"]) == 0:
                if attempt < max_retries - 1:
                    print(f"No emails found. Retrying in {interval} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(interval)
                    continue
            
            return data
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Request failed: {e}. Retrying in {interval} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(interval)
            else:
                print(f"An error occurred while calling Mailassert API: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response: {e.response.text}")
                raise

def extract_links_from_email(payload: Dict[str, Any]) -> List[str]:
    """
    Search emails and extract all URLs from the HTML body of the resulting emails.
    
    Args:
        payload (dict): Dictionary with search filters.
            
    Returns:
        list: A list of URLs extracted from the email bodies.
    """
    response = search_emails(payload)
    links = []
    
    # Check if the response contains the expected 'emails' list
    if isinstance(response, dict) and "emails" in response:
        for email in response.get("emails", []):
            body_html = email.get("bodyHtml", "")
            if body_html:
                # Find all href attributes in the HTML body
                # This basic regex matches: href="<url>" or href='<url>'
                extracted_links = re.findall(r'href=[\'"]?([^\'" >]+)', body_html)
                links.extend(extracted_links)
                
    return links


if __name__ == "__main__":
    print(extract_links_from_email({"to": "test2@automationtest-mytest.mailassert.com"}))