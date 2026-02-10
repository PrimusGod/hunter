import streamlit as st
import aiohttp
import asyncio
import pandas as pd
import plotly.express as px
import time

# --- CONFIGURATION ---
# We use the official Sherlock project's data file for the most up-to-date site list
DATA_URL = "https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock/resources/data.json"
MAX_CONCURRENT_REQUESTS = 50  # Prevent rate limiting
TIMEOUT_SECONDS = 10

# --- SETUP PAGE ---
st.set_page_config(page_title="DeepSearch OSINT Tool", page_icon="🔍", layout="wide")

st.markdown("""
<style>
    .main {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
    }
    .metric-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #41424b;
    }
</style>
""", unsafe_allow_html=True)

# --- ENGINE ---
async def fetch(session, site_name, site_data, username):
    url = site_data["url"].format(username)
    error_type = site_data.get("errorType")
    
    try:
        start_time = time.time()
        async with session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True) as response:
            latency = (time.time() - start_time) * 1000
            status = response.status
            text = await response.text()
            
            # Logic to determine if user exists based on Sherlock's methodology
            exists = False
            if error_type == "status_code":
                if status != 404:
                    exists = True
            elif error_type == "message":
                if site_data.get("errorMsg") not in text:
                    exists = True
            elif error_type == "response_url":
                if str(response.url) == url: # If not redirected
                    exists = True
            
            if exists:
                return {
                    "site": site_name,
                    "url": url,
                    "status": "Found",
                    "latency_ms": f"{latency:.0f}",
                    "category": "Social" # Placeholder for future categorization
                }
    except:
        pass
    return None

async def run_search(username, site_data):
    results = []
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        # Limit to top 200 sites for performance in this demo, or remove slice for full search
        for site_name, data in list(site_data.items())[:200]: 
            tasks.append(fetch(session, site_name, data, username))
        
        # Update progress bar
        progress_bar = st.progress(0)
        completed = 0
        total = len(tasks)
        
        for future in asyncio.as_completed(tasks):
            result = await future
            if result:
                results.append(result)
            completed += 1
            progress_bar.progress(completed / total)
            
    return results

# --- UI LAYOUT ---
st.title("🔍 Professional Deep Search Tool")
st.markdown("### Open Source Intelligence (OSINT) Scanner")
st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.info("💡 **How it works:** This tool scans hundreds of public platforms in real-time to find cross-site usage of a specific username.")
    target_username = st.text_input("Enter Target Username", placeholder="e.g. johndoe123")
    
    # Advanced Options (Collapsible)
    with st.expander("Advanced Configuration"):
        search_mode = st.radio("Search Depth", ["Fast (Top 200 Sites)", "Deep (All Sites)"])
        export_format = st.selectbox("Export Format", ["CSV", "JSON"])

    start_btn = st.button("🚀 Initiate Deep Search")

# --- MAIN EXECUTION ---
if start_btn and target_username:
    with col2:
        status_text = st.empty()
        status_text.write(f"🔄 Fetching latest site signatures...")
        
        # Load Data
        try:
            sites_df = pd.read_json(DATA_URL)
            if search_mode == "Fast (Top 200 Sites)":
                sites_data = dict(list(sites_df.items())[:200])
            else:
                sites_data = dict(list(sites_df.items()))
                
            status_text.write(f"🔎 Scanning {len(sites_data)} platforms for **'{target_username}'**...")
            
            # Run Async Search
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(run_search(target_username, sites_data))
            
            status_text.empty()
            
            if results:
                df = pd.DataFrame(results)
                
                # --- RESULTS DASHBOARD ---
                st.success(f"✅ Search Complete. Found {len(df)} matches.")
                
                # Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Matches Found", len(df))
                m2.metric("Avg Latency", f"{pd.to_numeric(df['latency_ms']).mean():.0f} ms")
                m3.metric("Coverage", f"{len(sites_data)} Sites")
                
                # Visualization
                # fig = px.bar(df, x='site', y='latency_ms', title="Response Times (ms)")
                # st.plotly_chart(fig, use_container_width=True)
                
                # Data Table
                st.dataframe(
                    df[['site', 'url', 'latency_ms']], 
                    column_config={
                        "url": st.column_config.LinkColumn("Profile Link")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Download
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Report",
                    csv,
                    "osint_report.csv",
                    "text/csv",
                    key='download-csv'
                )
            else:
                st.warning(f"❌ No matches found for '{target_username}'.")
                
        except Exception as e:
            st.error(f"An error occurred: {e}")

# Footer
st.markdown("---")
st.caption("⚠️ **Disclaimer:** This tool is for educational and professional OSINT research purposes only. Do not use for harassment or illegal tracking.")
              
