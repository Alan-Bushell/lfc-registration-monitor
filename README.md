# LFC Ticket Registration Monitor

A robust, containerized Python automation tool that monitors the [Liverpool FC Ticket Availability](https://www.liverpoolfc.com/tickets/tickets-availability) page. It detects upcoming "Additional Members Sales" and automatically adds them to your Google Calendar, ensuring you never miss a registration window.

## 🚀 Features

*   **Automated Scraping**: Uses Playwright (async) to navigate the LFC ticket portal and extract sale dates.
*   **Smart Parsing**: Identifies "Registration" and "Sale" dates for specific home games.
*   **Calendar Integration**: Adds events directly to your Google Calendar using the Google Calendar API.
*   **Duplicate Prevention**: Checks for existing events to avoid cluttering your calendar.
*   **Rich Details**: Events include the opponent name, sale type, and a direct link to the booking page.
*   **Cloud Ready**: Fully containerized with Docker and optimized for Google Cloud Run Jobs.

## 🛠️ Prerequisites

*   **Python 3.12+**
*   **Google Cloud Project** with the Calendar API enabled.
*   **Service Account Credentials** (`service_account.json`) with permission to edit your target calendar.

## ⚙️ Configuration

The application uses the following environment variables:

| Variable | Description | Required |
| :--- | :--- | :--- |
| `TARGET_CALENDAR_ID` | The email address of the Google Calendar to add events to (e.g., `your.email@gmail.com`). | Yes |

## 📦 Installation & Local Usage

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Alan-Bushell/lfc-registration-monitor.git
    cd lfc-registration-monitor
    ```

2.  **Set up the environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
    ```

3.  **Add Credentials:**
    Place your Google Service Account key file named `service_account.json` in the root directory.
    *Note: This file is git-ignored for security.*

4.  **Run the monitor:**
    ```bash
    export TARGET_CALENDAR_ID='your.email@gmail.com'
    python main.py
    ```

## 🐳 Docker Deployment (Google Cloud Run)

This project is designed to run as a scheduled job on Google Cloud Run.

### 1. Build the Image
```bash
# Ensure service_account.json is in the current directory
gcloud builds submit --tag europe-west2-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/lfc-monitor .
```

### 2. Create the Job
```bash
gcloud run jobs create lfc-monitor-job \
  --image europe-west2-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/lfc-monitor \
  --region europe-west2 \
  --set-env-vars TARGET_CALENDAR_ID=your.email@gmail.com
```

### 3. Schedule (Cron)
To run every 2 days at 9:00 AM:
```bash
gcloud scheduler jobs create http lfc-monitor-schedule \
  --location europe-west2 \
  --schedule "0 9 */2 * *" \
  --uri "https://europe-west2-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/[PROJECT_ID]/jobs/lfc-monitor-job:run" \
  --http-method POST \
  --oauth-service-account-email [PROJECT_NUMBER]-compute@developer.gserviceaccount.com
```

## 🔒 Security Note

*   **`service_account.json`**: This file contains sensitive keys. It is added to `.gitignore` and `.dockerignore` to prevent accidental commits.
*   **`.gcloudignore`**: Configured to *allow* uploading the key file only during Google Cloud builds, ensuring the container has access to credentials without exposing them in the source code.

## 📄 License

This project is for educational purposes only. Not affiliated with Liverpool Football Club.
