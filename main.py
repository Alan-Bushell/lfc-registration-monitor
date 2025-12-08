import asyncio
import logging
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import re
from create_calendar_event import create_event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

LFC_TICKETS_URL = "https://www.liverpoolfc.com/tickets/tickets-availability"


async def main():
    """
    Launches a browser, navigates to the LFC tickets page, finds home games
    in the next 30 days, and then navigates to each game's page to find
    additional members sale date. Generally AMS do not go on sale over
    2 weeks out from the game.
    """
    logging.info("Starting LFC Registration Monitor...")
    try:
        async with async_playwright() as p:
            # Launch with headless=True explicitly and set a user agent to avoid bot detection
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            logging.info(f"Navigating to {LFC_TICKETS_URL}")
            await page.goto(LFC_TICKETS_URL, timeout=60000) # 60s timeout

            await page.wait_for_selector(".tickets-listing")

            match_items = await page.query_selector_all(".tickets-listing li")

            today = datetime.now()
            thirty_days_from_now = today + timedelta(days=30)

            home_games_in_30_days = []

            for item in match_items:
                is_home_game = await item.query_selector('div.top.home')

                if is_home_game:
                    bottom_section = await item.query_selector('div.bottom.home')
                    if bottom_section:
                        bottom_text = await bottom_section.inner_text()
                        # The date is in the format "Day D MMM YYYY, H:MMam/pm"
                        # Example: "Tue 9 Dec 2025, 8:00pm"
                        date_match = re.search(r"(\w{3}\s\d{1,2}\s\w{3}\s\d{4})", bottom_text)
                        if date_match:
                            date_part = date_match.group(1)
                            try:
                                # The format is like "Tue 9 Dec 2025"
                                match_date = datetime.strptime(date_part, "%a %d %b %Y")
                                if today <= match_date <= thirty_days_from_now:
                                    link_element = await item.query_selector("a.ticket-card.fixture")
                                    if link_element:
                                        href = await link_element.get_attribute("href")
                                        home_games_in_30_days.append(href)
                            except ValueError:
                                # Handle cases where the date format is not as expected
                                logging.warning(f"Could not parse date: {date_part}")
            
            if home_games_in_30_days:
                logging.info(f"Found {len(home_games_in_30_days)} home games in the next 30 days.")
                for url in home_games_in_30_days:
                    full_url = f"https://www.liverpoolfc.com{url}"
                    logging.info(f"Processing game: {full_url}")
                    await page.goto(full_url, timeout=60000)
                    
                    try:
                        await page.wait_for_selector("#firstSet", timeout=5000)
                    except Exception:
                        logging.info("  Could not find sale information list for this game.")
                        continue

                    sale_list = await page.query_selector("#firstSet")
                    if sale_list:
                        # Extract opponent from URL
                        # URL format: /tickets/tickets-availability/liverpool-fc-v-opponent-name-date...
                        opponent_name = "Unknown Opponent"
                        url_match = re.search(r"liverpool-fc-v-(.+?)-\d{1,2}-[a-z]{3}-\d{4}", url.lower())
                        if url_match:
                            opponent_slug = url_match.group(1)
                            opponent_name = opponent_slug.replace('-', ' ').title()

                        sale_items = await sale_list.query_selector_all("li")
                        found_registration_info = False
                        
                        for sale_item in sale_items:
                            sale_name_element = await sale_item.query_selector(".salename")
                            if sale_name_element:
                                sale_name_raw = await sale_name_element.text_content()
                                sale_name_cleaned = sale_name_raw.replace('\n', '')
                                sale_name = ' '.join(sale_name_cleaned.split())

                                if sale_name == "Additional Members Sale Registration" or sale_name == "Additional Members Sale":
                                    when_available_element = await sale_item.query_selector(".whenavailable")
                                    if when_available_element:
                                        sale_date_str = await when_available_element.inner_text()
                                        logging.info(f"  Found {sale_name}: {sale_date_str.strip()}")
                                        
                                        try:
                                            sale_datetime = datetime.strptime(sale_date_str.strip(), "%a %d %b %Y, %I:%M%p")
                                            end_time = sale_datetime + timedelta(hours=1)
                                            
                                            event_title = f"LFC: {opponent_name} - {sale_name}"
                                            
                                            create_event(
                                                event_title,
                                                sale_datetime,
                                                end_time,
                                                description=full_url,
                                                color_id='11' # Red
                                            )
                                            found_registration_info = True
                                        except ValueError as e:
                                            logging.error(f"  Could not parse sale date: {e}")
                                    else:
                                        logging.warning(f"  Could not find date for {sale_name}.")
                        
                        if not found_registration_info:
                            logging.info("  Could not find 'Additional Members Sale' info for this game.")
                    else:
                        logging.info("  Could not find sale information list for this game.")

            else:
                logging.info("No home games found in the next 30 days.")

            await browser.close()
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
