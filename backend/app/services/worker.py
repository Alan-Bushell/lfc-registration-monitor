import asyncio
import logging
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.db.models import User, Event

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LFC_TICKETS_URL = "https://www.liverpoolfc.com/tickets/tickets-availability"

def add_calendar_event(user_email: str, refresh_token: str, title: str, start_time: datetime, url: str):
    """
    Adds an event to the user's primary Google Calendar.
    """
    try:
        # Load client config from env
        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
        
        if not client_id or not client_secret:
            logger.error(f"Missing Google Client ID/Secret for user {user_email}")
            return

        # Create credentials object from refresh token
        creds = Credentials(
            None, # access_token (will be refreshed)
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': f"LFC Ticket Sale: {title}",
            'location': 'Online',
            'description': f"Ticket sale for {title}. \nLink: {url}\n\nAutomated by LFC Monitor.",
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Europe/London',
            },
            'end': {
                'dateTime': (start_time + timedelta(hours=1)).isoformat(),
                'timeZone': 'Europe/London',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }

        service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Successfully added event '{title}' to {user_email}'s calendar.")

    except Exception as e:
        logger.error(f"Failed to add event for {user_email}: {e}")

async def process_new_event(title: str, start_time: datetime, url: str):
    """
    Check if event exists in DB. If not, save it and fan-out to all subscribers.
    """
    async with AsyncSessionLocal() as db:
        # Check if event exists
        result = await db.execute(select(Event).where(Event.title == title)) # Simple check by title for now
        existing = result.scalars().first()
        
        if existing:
            return # Already processed

        # Add Event to DB
        new_event = Event(title=title, event_date=start_time)
        db.add(new_event)
        
        # Get active subscribers
        active_users = await db.execute(select(User).where(User.subscription_status == "active"))
        users = active_users.scalars().all()
        
        logger.info(f"New Event Found: {title}. Notifying {len(users)} users.")
        
        for user in users:
            if user.google_refresh_token:
                # Run the synchronous Google API call in a thread pool to avoid blocking the async loop
                await asyncio.to_thread(
                    add_calendar_event, 
                    user.email, 
                    user.google_refresh_token, 
                    title, 
                    start_time, 
                    url
                )
        
        await db.commit()

async def check_lfc_site():
    logger.info("Starting Scrape...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Random User Agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            await page.goto(LFC_TICKETS_URL, timeout=60000)
            await page.wait_for_selector(".tickets-listing")
            match_items = await page.query_selector_all(".tickets-listing li")
            
            # Logic similar to original script
            today = datetime.now()
            thirty_days_from_now = today + timedelta(days=30)
            
            for item in match_items:
                is_home = await item.query_selector('div.top.home')
                if is_home:
                    bottom = await item.query_selector('div.bottom.home')
                    if bottom:
                        text = await bottom.inner_text()
                        # Date Format: Tue 9 Dec 2025
                        match = re.search(r"(\w{3}\s\d{1,2}\s\w{3}\s\d{4})", text)
                        if match:
                            try:
                                match_date = datetime.strptime(match.group(1), "%a %d %b %Y")
                                if today <= match_date <= thirty_days_from_now:
                                    link = await item.query_selector("a.ticket-card.fixture")
                                    if link:
                                        href = await link.get_attribute("href")
                                        full_url = f"https://www.liverpoolfc.com{href}"
                                        opponent_name = "Unknown Opponent"
                                        if href:
                                            slug_match = re.search(
                                                r"liverpool-fc-v-(.+?)-\d{1,2}-[a-z]{3}-\d{4}",
                                                href.lower(),
                                            )
                                            if slug_match:
                                                opponent_name = slug_match.group(1).replace("-", " ").title()
                                        
                                        # Go to game page
                                        # We open a new page or reuse? Reuse is faster for single thread
                                        logger.info(f"Checking game: {full_url}")
                                        game_page = await context.new_page()
                                        await game_page.goto(full_url, timeout=60000)
                                        
                                        # Scrape sales
                                        try:
                                            await game_page.wait_for_selector("#firstSet", timeout=5000)
                                            sale_items = await game_page.query_selector_all("#firstSet li")
                                            for sale in sale_items:
                                                name_el = await sale.query_selector(".salename")
                                                if name_el:
                                                    name_text = await name_el.text_content()
                                                    clean_name = ' '.join(name_text.strip().split())
                                                    
                                                    if "Additional Members Sale" in clean_name:
                                                        date_el = await sale.query_selector(".whenavailable")
                                                        if date_el:
                                                            date_str = await date_el.inner_text()
                                                            # Format: Tue 9 Dec 2025, 8:00pm
                                                            try: 
                                                                sale_date = datetime.strptime(date_str.strip(), "%a %d %b %Y, %I:%M%p")
                                                                title = f"LFC: {opponent_name} - {clean_name}"
                                                                await process_new_event(title, sale_date, full_url)
                                                            except Exception as e:
                                                                logger.error(f"Date parse error: {e}")
                                        except Exception as e:
                                            logger.info(f"No sale info found/timeout: {full_url}")
                                        finally:
                                            await game_page.close()
                            except ValueError:
                                pass

        except Exception as e:
            logger.error(f"Error scraping: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check_lfc_site())
