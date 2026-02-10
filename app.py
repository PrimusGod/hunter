import streamlit as st
import aiohttp
import asyncio
import pandas as pd
import time
import nest_asyncio
import urllib.parse

# --- CRITICAL FIXES ---
nest_asyncio.apply()

# --- CONFIGURATION ---
DATA_URL = "https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock_project/resources/data.json"
MAX_CONCURRENT_REQUESTS = 20
TIMEOUT_SECONDS = 5

# --- PAGE CONFIG ---
st.set_page_config(page_title="EagleEye OSINT", page_icon="🦅", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #262730;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- ENGINE 1: ASYNC USERNAME SEARCH ---
async def fetch(session, site_name, site_data, username):
    url = site_data["url"].format(username)
    error_type = site_data.get("errorType")
    
    try:
        start_time = time.time()
        async with session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True) as response:
            latency = (time.time() - start_time) * 1000
            status = response.status
            text = await response.text()
            
            exists = False
            # Sherlock Logic
            if error_type == "status_code":
                if status != 404: exists = True
            elif error_type == "message":
                if site_data.get("errorMsg") not in text: exists = True
            elif error_type == "response_url":
                if str(response.url) == url: exists = True
            
            if exists:
                return {"site": site_name, "url": url, "latency": f"{latency:.0f}ms"}
    except:
        pass
    return None

async def run_username_search(username, site_data):
    results = []
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, name, data, username) for name, data in site_data.items()]
        
        progress = st.progress(0)
        status = st.empty()
        completed = 0
        total = len(tasks)
        
        for future in asyncio.as_completed(tasks):
            result = await future
            if result: results.append(result)
            completed += 1
            if completed % 10 == 0:
                progress.progress(completed / total)
                status.caption(f"Scanned {completed}/{total} sites...")
                
        progress.empty()
        status.empty()
    return results

# --- ENGINE 2: GOOGLE DORK GENERATOR ---
def generate_dorks(first, last, location, keywords):
    name = f'"{first} {last}"'
    loc = f'"{location}"' if location else ""
    keys = f'"{keywords}"' if keywords else ""
    
    # Common Dating & Social Patterns
    platforms = {
        "Dating: Tinder": f'site:tinder.com {name} {loc} -inurl:tinder.com/app',
        "Dating: Bumble": f'site:bumble.com {name} {loc}',
        "Dating: OkCupid": f'site:okcupid.com/profile {name} {loc}',
        "Dating: POF": f'site:pof.com {name} {loc}',
        "Social: Facebook": f'site:facebook.com {name} {loc} {keys}',
        "Social: Instagram": f'site:instagram.com {name} {loc}',
        "Social: Twitter/X": f'site:twitter.com {name} {loc}',
        "Social: LinkedIn": f'site:linkedin.com/in {name} {loc} {keys}',
        "General: Mentions": f'{name} {loc} {keys} -site:facebook.com -site:linkedin.com'
    }
    
    return platforms

# --- MAIN APP UI ---
st.title("🦅 EagleEye: Professional OSINT Tool")

tab1, tab2 = st.tabs(["🆔 Username Search", "🕵️ Person Deep Search"])

# === TAB 1: USERNAME SEARCH ===
with tab1:
    st.markdown("### Scan for a username across 400+ platforms")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        target_username = st.text_input("Enter Username", placeholder="e.g. johndoe123")
        search_mode = st.radio("Scan Depth", ["Fast (Top 50)", "Deep (All Sites)"], horizontal=True)
        start_scan = st.button("🚀 Start Scan", use_container_width=True)

    with col2:
        if start_scan and target_username:
            try:
                sites_df = pd.read_json(DATA_URL)
                sites_data = dict(list(sites_df.items())[:50]) if "Fast" in search_mode else dict(list(sites_df.items()))
                
                st.info(f"Scanning {len(sites_data)} sites for '{target_username}'...")
                loop = asyncio.get_event_loop()
                results = loop.run_until_complete(run_username_search(target_username, sites_data))
                
                if results:
                    df = pd.DataFrame(results)
                    st.success(f"Found {len(df)} profiles!")
                    st.dataframe(
                        df, 
                        column_config={"url": st.column_config.LinkColumn("Profile Link")}, 
                        use_container_width=True, 
                        hide_index=True
                    )
                else:
                    st.warning("No profiles found.")
            except Exception as e:
                st.error(f"Error: {e}")

# === TAB 2: PERSON DEEP SEARCH (DORKING) ===
with tab2:
    st.markdown("### Find people by Name, Location, & Keywords")
    st.info("ℹ️ **How this works:** This tool constructs advanced 'Google Dorks' to bypass search restrictions on dating and social sites. It finds public profiles indexed by search engines.")
    
    c1, c2, c3 = st.columns(3)
    first_name = c1.text_input("First Name")
    last_name = c2.text_input("Last Name")
    location = c3.text_input("Location (City/State)", placeholder="e.g. Chicago")
    keywords = st.text_input("Keywords / Job / Hobbies", placeholder="e.g. Nurse, Hiking, Engineer")
    
    if st.button("🔎 Generate Deep Search Links", type="primary", use_container_width=True):
        if not first_name or not last_name:
            st.error("Please enter at least a First and Last Name.")
        else:
            dorks = generate_dorks(first_name, last_name, location, keywords)
            
            st.markdown("---")
            st.subheader("🎯 Direct Search Links")
            st.caption("Click the buttons below to open a 'Deep Search' in a new tab.")
            
            for platform, query in dorks.items():
                encoded_query = urllib.parse.quote(query)
                google_link = f"https://www.google.com/search?q={encoded_query}"
                
                # Visual rendering of links
                st.markdown(f"""
                <a href="{google_link}" target="_blank" style="text-decoration: none;">
                    <div style="
                        background-color: #262730; 
                        padding: 15px; 
                        border-radius: 8px; 
                        margin-bottom: 10px; 
                        border-left: 5px solid #ff4b4b;
                        color: white;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;">
                        <span style="font-weight: bold; font-size: 1.1em;">{platform}</span>
                        <span style="background-color: #ff4b4b; padding: 5px 10px; border-radius: 5px; font-size: 0.8em;">OPEN SEARCH ↗</span>
                    </div>
                </a>
                """, unsafe_allow_html=True)

st.markdown("---")
st.caption("⚠️ **Legal Disclaimer:** This tool aggregates publicly available data. Do not use for stalking, harassment, or illegal purposes.")
    
