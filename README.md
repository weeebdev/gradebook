# Gradebook App

A Streamlit application that allows students to view their grades from a Google Spreadsheet using Google authentication.

## Features

- Google Authentication for secure login
- Extracts student ID from email (e.g., 1801@gmail.com → ID: 1801)
- Fetches student grades from a Google Spreadsheet
- Displays personalized grade information

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Cloud Setup

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Sheets API and Google Drive API

#### OAuth Client Setup (for user authentication)
1. Configure the OAuth consent screen:
   - Set User Type to "External"
   - Add the scopes for email and profile information
   - Add your test users
2. Create OAuth client ID:
   - Select "Web application" as the application type
   - Add "http://localhost:8501" to the Authorized redirect URIs
   - Download the credentials as JSON
   - Rename the file to `credentials.json` and place it in the project root

#### Service Account Setup (for spreadsheet access)
1. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name and description
   - Grant it the "Viewer" role
2. Create a key for the service account:
   - Select the service account you just created
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the key file
   - Rename the file to `service-account.json` and place it in the project root

### 3. Google Spreadsheet Setup

1. Create a Google Spreadsheet with the following structure:
   - First column should be named "ID" and contain student IDs
   - Other columns should contain grades for different subjects/assignments
2. Share the spreadsheet with the service account email from your Google Cloud project:
   - Click the "Share" button in your Google Spreadsheet
   - Enter the service account email (found in the `service-account.json` file under "client_email")
   - Grant it "Viewer" access
   - Click "Share"
3. Copy the Spreadsheet ID from the URL:
   - The Spreadsheet ID is the long string in the URL between /d/ and /edit
   - For example, in `https://docs.google.com/spreadsheets/d/1tvpuPNhB5-RBDaXK5Gg8q0WnEp34EgeYtjy0GreARXk/edit`, the ID is `1tvpuPNhB5-RBDaXK5Gg8q0WnEp34EgeYtjy0GreARXk`

### 4. Environment Variables

Create a `.env` file in the project root with the following variables:

```
SPREADSHEET_ID=your_spreadsheet_id_here
```

### 5. Run the Application

```bash
streamlit run app.py
```

## Usage

1. Click the "Login with Google" button
2. Authorize the application (only email and profile information will be requested)
3. Enter the authorization code in the application
4. View your grades displayed in the dashboard
