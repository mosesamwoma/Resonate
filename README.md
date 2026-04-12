# Resonate 

A personal Spotify analytics app that gives you **Monthly & Weekly Wrapped** — without waiting for December.

Resonate fetches your Spotify listening history, stores it in PostgreSQL and serves interactive dashboards. Choose between a **Django web app** or a **Streamlit dashboard** — they run independently.

---
## Features
- Spotify Login via OAuth 2.0
- **Monthly Wrapped** — top tracks & artists per calendar month
- **Weekly Wrapped** — weekly breakdowns within any selected month
- Interactive charts built with Plotly
- PostgreSQL for persistent historical tracking
- Long-term trend monitoring
---
## Setup
### 1. Clone the repository
```bash
git clone https://github.com/mosesamwoma/Resonate.git
cd Resonate
```
### 2. Create and activate a virtual environment
**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```
**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```
### 3. Install dependencies
```bash
pip install -r requirements.txt
```
### 4. Configure environment variables
Get your Spotify API credentials at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
Create a `.env` file in the root directory:
```env
CLIENT_ID=<your_spotify_client_id>
CLIENT_SECRET=<your_spotify_client_secret>
REDIRECT_URI=http://localhost:8501
DATABASE_URL=postgres://resonate_user:yourpassword@localhost:5432/resonate_db
```
### 5. Set up PostgreSQL
**Install:**
- Download and install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/) — pgAdmin is bundled in the installer
- During installation, set a password for the `postgres` superuser and keep it
**Create the database in pgAdmin:**
- Open pgAdmin → log in with your `postgres` password
- Left panel: **Servers** → **PostgreSQL** → right-click **Databases** → **Create** → **Database**
- Set **Database name**: `resonate_db` → click **Save**
**Create a user:**
- Right-click **Login/Group Roles** → **Create** → **Login/Group Role**
- **General** tab → Name: `resonate_user`
- **Definition** tab → set a password
- **Privileges** tab → enable **Can login** and **Superuser** → click **Save**
**Set ownership:**
- Right-click `resonate_db` → **Properties** → **General** tab → set **Owner** to `resonate_user` → click **Save**
### 6. Apply Django migrations (web version only)
```bash
python manage.py migrate
```
---
## Running the App
Pick **one** — web and Streamlit run independently, not simultaneously.
---
### Option A — Django Web App
![Web Interface](assets/1.jpeg)
```bash
python manage.py runserver
```
Opens at `http://127.0.0.1:8000`
---
### Option B — Streamlit Dashboard
![Streamlit Interface](assets/2.jpeg)
Get your Spotify API credentials at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
Before running, create the secrets file at `resonate/streamlit_version/.streamlit/secrets.toml`:
```toml
SPOTIPY_CLIENT_ID = "your_spotify_client_id"
SPOTIPY_CLIENT_SECRET = "your_spotify_client_secret"
SPOTIPY_REDIRECT_URI = "http://localhost:8501"
```
Then run:
```bash
cd resonate/streamlit_version
streamlit run resonate.py
```
Opens at `http://localhost:8501`
---
## Usage
1. Open the app in your browser
2. Click **Login with Spotify**
3. Select a month to view your **Monthly Wrapped**
4. Optionally select a week for **Weekly Wrapped**
5. Data is saved to PostgreSQL for historical analysis
---
## Limitations
| Limitation | Workaround |
|---|---|
| Spotify API returns last 50 tracks only | Schedule daily fetches; persist all to PostgreSQL |
| No retroactive history | Start collecting now; optionally import CSV exports |
| API rate limits | Batch requests; retry on error |
---
## Future Enhancements
- Trend charts across multiple months
- Downloadable PDF Wrapped reports
- Daily scheduled data collection
- Heatmaps and shareable Wrapped images
- Playlist export
---
## Contributing
Contributions are welcome! To contribute:
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

Please ensure your code follows the existing style and includes tests where applicable.
---
**Built with Python, Django, Streamlit, PostgreSQL & Plotly**
