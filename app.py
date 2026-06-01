import streamlit as st
from playwright.sync_api import sync_playwright
import pandas as pd
import time

# --- 1. THE SCRAPING FUNCTION ---
def scrape_starlink_data(username, password, progress_box):
    data = []
    
    with sync_playwright() as p:
        progress_box.info("🤖 Launching visual browser session...")
        
        browser = p.chromium.launch(
            headless=False, 
            slow_mo=200,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        
        try:
            progress_box.info("🌐 Navigating to Starlink Login...")
            page.goto("https://www.starlink.com/account/home")
            page.wait_for_load_state("domcontentloaded")
            progress_box.info("🔑 Waiting for email input field to render...")
            
            email_input = page.locator("input[name='email']")
            email_input.wait_for(state="visible", timeout=25000)
            email_input.fill(username)
            
            progress_box.info("🔑 Entering password...")
            password_input = page.locator("input[name='password']")
            password_input.wait_for(state="visible", timeout=15000)
            password_input.fill(password)
            
            login_button = page.get_by_role("button", name="Sign In") 
            login_button.wait_for(state="visible", timeout=15000)
            login_button.click()
            
            progress_box.info("🔄 Waiting for dashboard redirection...")
            page.wait_for_url("**/account/home", timeout=30000) 
            page.wait_for_load_state("domcontentloaded")
            
            progress_box.info("🎯 Locating and clicking 'Your Subscription'...")
            subscription_card = page.get_by_text("Your Subscription")
            subscription_card.wait_for(state="visible", timeout=15000)
            subscription_card.click()
            
            progress_box.info("📊 Loading chart elements...")
            page.wait_for_load_state("domcontentloaded")
            
            # --- SCRAPE DATA (SVG CHART HOVER METHOD) ---
            
            chart_bar_selector = "rect.MuiBarElement-series-y_0"
            page.wait_for_selector(chart_bar_selector, timeout=25000)
            
            bars = page.locator(chart_bar_selector).all()
            total_bars = len(bars)
            
            if total_bars == 0:
                progress_box.warning("Chart layer found, but individual data nodes are empty.")
                return data

            progress_box.info(f"🕸️ Found {total_bars} bars. Executing forced coordinate hover extractions...")
            
            for i, bar in enumerate(bars):
                try:
                    bar.scroll_into_view_if_needed()
                    bar.hover(force=True, timeout=3000)

                    time.sleep(0.4) 
                    
                    tooltip = page.locator(".MuiChartsTooltip-root")
                    
                    if tooltip.is_visible():
                        date_val = tooltip.locator("caption").inner_text().strip()
                        usage_val = tooltip.locator("td.MuiChartsTooltip-valueCell").inner_text().strip()
                        
                        if not data or data[-1]["Date"] != date_val:
                            data.append({"Date": date_val, "Data Usage (GB)": usage_val})
                            
                except Exception as bar_error:
                    continue
                    
                if i % 5 == 0 or i == total_bars - 1:
                    progress_box.info(f"🕵️‍♂️ Reading chart: {i+1}/{total_bars} points captured...")
                    
        except Exception as e:
            st.error(f"Scraper structural failure at current step: {e}")
            
        finally:
            browser.close()
            
    return data

# --- 2. THE WEB UI (FRONTEND) ---
st.set_page_config(page_title="Starlink Data Scraper", page_icon="📡")

st.title("📡 Starlink Daily Data Extraper")
st.markdown("Enter credentials below to safely extract and build your daily usage telemetry report. 📊")

username = st.text_input("Username", value="fundamentalssystem@gmail.com")
password = st.text_input("Password", type="password") 

if st.button("Start Webscraping 🕸️"):
    if not password:
        st.warning("Please enter the operational password to proceed.")
    else:
        progress_box = st.empty()
        
        scraped_data = scrape_starlink_data(username, password, progress_box)
        
        if scraped_data:
            progress_box.success("Data compiled successfully! 🎉")
            
            df = pd.DataFrame(scraped_data)
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Download Data as .csv 💾",
                data=csv,
                file_name='starlink_daily_usage.csv',
                mime='text/csv',
            )
        elif len(scraped_data) == 0:
            progress_box.error("Navigation pipeline cleared, but data payload returned empty. Verify panel path state.")
