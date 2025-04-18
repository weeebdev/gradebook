import re
import time
import socket
import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import urllib.parse

# Set page configuration
st.set_page_config(
    page_title="Student Gradebook",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
# Only request user profile information, not spreadsheet access
OAUTH_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]
# Separate scopes for service account
SERVICE_ACCOUNT_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]
SPREADSHEET_ID = st.secrets["spreadsheet_id"]

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'grades_data' not in st.session_state:
    st.session_state.grades_data = None
if 'student_id' not in st.session_state:
    st.session_state.student_id = None
if 'auth_code' not in st.session_state:
    st.session_state.auth_code = None

def extract_student_id(email):
    """Extract student ID from email address (e.g., 1801@gmail.com -> 1801)"""
    id = email.split('@')[0]
    return id

def get_user_info(credentials, max_retries=3, timeout=10):
    """Get user info from Google API with retry mechanism"""
    for attempt in range(max_retries):
        try:
            print(f"Starting to get user info (attempt {attempt+1}/{max_retries})...")
            print(f"Credentials: {credentials}")
            
            # Set socket timeout
            socket.setdefaulttimeout(timeout)
            
            # Build the service with explicit timeout
            service = build('oauth2', 'v2', credentials=credentials)
            print("OAuth2 service built successfully.")
            
            print("Calling userinfo().get()...")
            user_info = service.userinfo().get().execute()
            print(f"User info retrieved successfully: {user_info}")
            return user_info
            
        except socket.timeout:
            print(f"Timeout error on attempt {attempt+1}/{max_retries}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("Maximum retry attempts reached")
                st.error("Connection to Google API timed out. Please try again later.")
                return None
                
        except HttpError as e:
            print(f"HTTP error on attempt {attempt+1}/{max_retries}: {e}")
            if e.resp.status in [429, 500, 502, 503, 504]:  # Retryable status codes
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print("Maximum retry attempts reached")
                    st.error(f"Google API error: {e}")
                    return None
            else:
                # Non-retryable error
                print(f"Non-retryable HTTP error: {e}")
                st.error(f"Google API error: {e}")
                return None
                
        except Exception as e:
            print(f"ERROR getting user info: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            st.error(f"Error getting user info: {e}")
            return None
    
    return None  # Shouldn't reach here, but just in case

def get_service_account_credentials():
    """Get service account credentials from Streamlit secrets"""
    # Create a dictionary from the secrets
    service_account_info = dict(st.secrets["gcp_service_account"])
    
    # Create credentials
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=SERVICE_ACCOUNT_SCOPES
    )
    
    return credentials

def fetch_all_grades():
    """Fetch all grades from the Google Spreadsheet"""
    try:
        # Use service account credentials from secrets
        credentials = get_service_account_credentials()
        print("Service account credentials loaded successfully.")
        
        # Create a gspread client using the service account credentials
        gc = gspread.authorize(credentials)
        print("Service account credentials loaded successfully.")
        
        # Open the spreadsheet
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        print(f"Spreadsheet opened successfully: {SPREADSHEET_ID}")
        
        # Get the first worksheet
        worksheet = spreadsheet.get_worksheet(0)
        print("First worksheet retrieved successfully.")
        
        # Get all records from the worksheet
        records = worksheet.get_all_records()
        print("Records retrieved successfully.", records)
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        return df
    except Exception as e:
        st.error(f"Error fetching grades: {e}")
        st.error(f"Details: {str(e)}")
        return None

def fetch_student_grades(student_id):
    """Fetch grades for a specific student ID"""
    try:
        # Get all grades
        print("Fetching all grades...")
        all_grades = fetch_all_grades()
        print("All grades fetched successfully.")
        
        if all_grades is None:
            return None
        
        # Find the row with the matching student ID
        student_row = all_grades[all_grades['ID'] == student_id]
        
        if student_row.empty:
            st.error(f"No records found for student ID: {student_id}")
            return None
        
        return student_row
    except Exception as e:
        st.error(f"Error fetching student grades: {e}")
        return None

def display_grades(grades_data):
    """Display the grades in a nice format"""
    if grades_data is None or grades_data.empty:
        return
    
    st.subheader("Your Grades")
    
    # Transpose the DataFrame for better display
    grades_transposed = grades_data.T.reset_index()
    grades_transposed.columns = ['Subject', 'Grade']
    
    # Remove the ID row since we don't need to display it
    grades_transposed = grades_transposed[grades_transposed['Subject'] != 'ID']
    
    # Create three columns for better layout
    col1, col2, col3 = st.columns(3)
    
    # Calculate how many subjects to show in each column
    n_subjects = len(grades_transposed)
    subjects_per_column = n_subjects // 3 + (1 if n_subjects % 3 > 0 else 0)
    
    # Display subjects in columns
    for i, col in enumerate([col1, col2, col3]):
        start_idx = i * subjects_per_column
        end_idx = min((i + 1) * subjects_per_column, n_subjects)
        
        if start_idx < n_subjects:
            with col:
                for _, row in grades_transposed.iloc[start_idx:end_idx].iterrows():
                    subject = row['Subject']
                    grade = row['Grade']
                    
                    # Create a card-like display for each grade
                    with st.container(border=True):
                        st.markdown(f"**{subject}**")
                        
                        # Determine color based on grade value
                        try:
                            grade_value = float(grade)
                            if grade_value >= 90:
                                color = "green"
                            elif grade_value >= 70:
                                color = "orange"
                            else:
                                color = "red"
                        except (ValueError, TypeError):
                            color = "blue"  # Default color for non-numeric grades
                        
                        st.markdown(f"<h3 style='color:{color};text-align:center;'>{grade}</h3>", 
                                    unsafe_allow_html=True)

def extract_auth_code_from_url(url):
    """Extract the authorization code from the redirect URL"""
    try:
        # Parse the URL
        parsed_url = urllib.parse.urlparse(url)
        
        # Get the query parameters
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Extract the code
        if 'code' in query_params:
            return query_params['code'][0]
        
        return None
    except Exception as e:
        st.error(f"Error extracting code from URL: {e}")
        return None

def get_oauth_client_config():
    """Get OAuth client configuration from Streamlit secrets"""
    # Create the client config dictionary in the format expected by Flow
    client_config = {
        "web": {
            "client_id": st.secrets["oauth"]["client_id"],
            "project_id": st.secrets["oauth"]["project_id"],
            "auth_uri": st.secrets["oauth"]["auth_uri"],
            "token_uri": st.secrets["oauth"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["oauth"]["auth_provider_x509_cert_url"],
            "client_secret": st.secrets["oauth"]["client_secret"],
            "redirect_uris": st.secrets["oauth"]["redirect_uris"],
            "javascript_origins": st.secrets["oauth"]["javascript_origins"]
        }
    }
    return client_config

def process_auth_code():
    """Process the authentication code and get user info"""
    if st.session_state.auth_code:
        try:
            print(f"Processing auth code: {st.session_state.auth_code[:10]}...")
            # Use redirect_uri from Streamlit secrets for deployment flexibility
            redirect_uri = st.secrets["oauth"]["redirect_uri"]
            flow = Flow.from_client_config(
                get_oauth_client_config(),
                scopes=OAUTH_SCOPES,
                redirect_uri=redirect_uri
            )
            print("Flow created successfully.")
            
            try:
                print("Fetching token...")
                # Exchange the authorization code for credentials
                flow.fetch_token(code=st.session_state.auth_code)
                print("Token fetched successfully.")
                
                # Get user info
                print("Getting user info...")
                user_info = get_user_info(flow.credentials)
                print(f"User info result: {user_info}")
                if user_info:
                    st.session_state.user_info = user_info
                    
                    # Extract student ID from email
                    email = user_info.get('email', '')
                    print(f"User email: {email}")
                    student_id = extract_student_id(email)
                    print(f"Extracted student ID: {student_id}")
                    
                    if student_id:
                        st.session_state.student_id = student_id
                        
                        # Fetch grades using service account
                        print(f"Fetching grades for student ID: {student_id}")
                        grades_data = fetch_student_grades(student_id)
                        print(f"Grades data fetched: {grades_data is not None}")
                        if grades_data is not None:
                            st.session_state.grades_data = grades_data
                            st.session_state.authenticated = True
                            return True
                    else:
                        st.error(f"Could not extract student ID from email: {email}")
            except Exception as e:
                error_message = str(e)
                if "invalid_grant" in error_message:
                    st.error("The authorization code has expired or already been used. Please try logging in again.")
                    # Reset the auth code so the user can try again
                    st.session_state.auth_code = None
                else:
                    st.error(f"Error during token exchange: {error_message}")
                return False
            
        except Exception as e:
            st.error(f"Error during authentication setup: {e}")
    
    return False

def main():
    # App title
    st.title("Student Gradebook")
    
    # Check if SPREADSHEET_ID is set
    if not SPREADSHEET_ID:
        st.error("Spreadsheet ID not found in secrets. Please check your .streamlit/secrets.toml file.")
        return
    
    # If user is not authenticated, show login button
    if not st.session_state.authenticated:
        st.write("Please login with your Google account to view your grades.")
        
        # Check for URL parameters (this happens after redirect from Google)
        if 'code' in st.query_params and not st.session_state.auth_code:
            auth_code = st.query_params['code']
            st.session_state.auth_code = auth_code
            st.info("Authorization code received! Processing...")
            
            # Process the auth code
            success = process_auth_code()
            
            # Clear the URL parameters regardless of success
            st.query_params.clear()
            
            if success:
                st.experimental_rerun()
            # If not successful, the error message will be displayed and user can try again
        
        # If no code in URL, show login button
        if not st.session_state.auth_code:
            if st.button("Login with Google"):
                # Create the flow using the client config from secrets
                client_config = get_oauth_client_config()
                # Use redirect_uri from Streamlit secrets for deployment flexibility
                redirect_uri = st.secrets["oauth"]["redirect_uri"]
                flow = Flow.from_client_config(
                    client_config,
                    scopes=OAUTH_SCOPES,
                    redirect_uri=redirect_uri
                )
                
                # Generate the authorization URL
                auth_url, _ = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true'
                )
                
                # Redirect the user to the authorization URL
                st.markdown(f"[Click here to authorize]({auth_url})")
                
                # Option to manually enter the URL
                st.write("After authorization, you'll be redirected to a URL. If automatic detection doesn't work, paste the full URL here:")
                redirect_url = st.text_input("Redirect URL:")
                
                if redirect_url:
                    auth_code = extract_auth_code_from_url(redirect_url)
                    if auth_code:
                        st.session_state.auth_code = auth_code
                        if process_auth_code():
                            st.experimental_rerun()
                    else:
                        st.error("Could not extract authorization code from the URL.")
    
    # If user is authenticated, show the dashboard
    else:
        # Display user info
        user_info = st.session_state.user_info
        if user_info:
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.image(user_info.get('picture', ''), width=100)
            
            with col2:
                st.subheader(f"Welcome, {user_info.get('name', 'Student')}!")
                st.write(f"Email: {user_info.get('email', '')}")
                st.write(f"Student ID: {st.session_state.student_id}")
        
        # Display grades
        if st.session_state.grades_data is not None:
            display_grades(st.session_state.grades_data)
        
        # Logout button
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.experimental_rerun()

if __name__ == "__main__":
    main()
