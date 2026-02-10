import streamlit as st
import aiohttp
import asyncio
import pandas as pd
import time
import nest_asyncio

# --- CRITICAL FIX FOR DEPLOYMENT ---
nest_asyncio.apply()

# --- CONFIGURATION ---
# UPDATED URL: The Sherlock project moved the file to 'sherlock_project/resources'
DATA_URL = "https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock_project/resources/data.json"
MAX_CONCURRENT_REQUESTS = 20
TIMEOUT_SECONDS = 5

# --- SETUP PAGE ---
st.set_page_config(page_title="DeepSearch OSINT Tool", page_icon="🔍", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; color: #fafafa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; }
    .metric-card { background-color: #262730; padding: 20px; border-radius: 10px; border: 1px solid #41424b; }
</style>
""", unsafe_allow_html=True)

# --- ASYNC SEARCH ENGINE ---
async def fetch(session, site_name, site_data, username):
    url = site_data["url"].format(username)
    error_type = site_data.get("errorType")
    
    try:
        start_time = time.time()
        # prevent redirects for speed unless necessary
        async with session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True) as response:
            latency = (time.time() - start_time) * 1000
            status = response.status
            text = await response.text()
            
            exists = False
            
            # Sherlock Logic
            if error_type == "status_code":
                if status != 404:
                    exists = True
            elif error_type == "message":
                if site_data.get("errorMsg") not in text:
                    exists = True
            elif error_type == "response_url":
                if str(response.url) == url:
                    exists = True
            
            if exists:
                return {
                    "site": site_name,
                    "url": url,
                    "status": "Found",
                    "latency_ms": f"{latency:.0f}"
                }
    except:
        pass
    return None

async def run_search(username, site_data):
    results = []
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for site_name, data in site_data.items():
            tasks.append(fetch(session, site_name, data, username))
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        completed = 0
        total = len(tasks)
        
        for future in asyncio.as_completed(tasks):
            result = await future
            if result:
                results.append(result)
            
            completed += 1
            if completed % (total // 10) == 0: # Update less frequently to save memory
                 progress_bar.progress(completed / total)
                 status_text.text(f"Scanned {completed}/{total} sites...")
                 
        progress_bar.empty()
        status_text.empty()
            
    return results

# --- UI LAYOUT ---
st.title("🔍 Professional Deep Search Tool")
st.caption("Advanced OSINT Username Scanner")

col1, col2 = st.columns([1, 2])

with col1:
    st.info("💡 **Instructions:** Enter a username. The system will scan 400+ social networks, coding platforms, and forums.")
    target_username = st.text_input("Target Username", placeholder="e.g. johndoe123")
    
    with st.expander("⚙️ Search Settings"):
        search_mode = st.radio("Depth", ["Fast (Top 50 Sites)", "Deep (All Sites)"])

    start_btn = st.button("🚀 Start Scan")

# --- MAIN EXECUTION ---
if start_btn and target_username:
    with col2:
        try:
            # 1. Load Data
            with st.spinner("Fetching latest site signatures..."):
                try:
                    sites_df = pd.read_json(DATA_URL)
                except Exception as e:
                    st.error(f"Failed to load site data: {e}")
                    st.stop()
                
                if search_mode == "Fast (Top 50 Sites)":
                    sites_data = dict(list(sites_df.items())[:50])
                else:
                    sites_data = dict(list(sites_df.items()))

            # 2. Execute Async Search
            st.write(f"🔎 Scanning **{len(sites_data)}** platforms for '{target_username}'...")
            
            loop = asyncio.get_event_loop()
            results = loop.run_until_complete(run_search(target_username, sites_data))
            
            # 3. Display Results
            if results:
                df = pd.DataFrame(results)
                st.success(f"✅ Found {len(df)} matches!")
                
                m1, m2 = st.columns(2)
                m1.metric("Matches", len(df))
                m2.metric("Scan Time", "Completed")
                
                st.dataframe(
                    df[['site', 'url']],
                    column_config={
                        "url": st.column_config.LinkColumn("Profile Link", display_text="View Profile")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Results (CSV)", csv, "osint_results.csv", "text/csv")
                
            else:
                st.warning(f"❌ No accounts found for '{target_username}'.")
                
        except Exception as e:
            st.error(f"System Error: {e}")
            
