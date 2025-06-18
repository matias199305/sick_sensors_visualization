import streamlit as st
import re
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def looks_like_datetime(txt):
    """True if the cell matches ISO-8601 date-time style: 2025-05-26T14:58:59"""
    return re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", txt)

def load_data(file_path):
    blocks = []
    
    with open(file_path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:                         # skip blank lines
                continue
            # ---------- 1) metadata row -----------------------------------------
            # Ignore header or any malformed line that isn't a timestamp.
            parts = [cell.strip() for cell in line.split(";")]
            if len(parts) != 5 or not looks_like_datetime(parts[0]):
                continue                         # <-- skip header here
            ts, h, gab, ang, fph = parts

            # ---------- 2) literal "SCAN" line ----------------------------------
            next(fh)                             # discard "SCAN"

            # ---------- 3) X row -------------------------------------------------
            x_row = next(fh).strip().split(";")[2:]   # drop "X" + empty col
            # ---------- 4) Y row -------------------------------------------------
            y_row = next(fh).strip().split(";")[2:]   # drop "Y" + empty col

            blocks.append({
                "DateTime": ts,
                "Height":          float(h),
                "Gab":             float(gab),
                "Angle":           float(ang),
                "FixedPointHeight":float(fph),
                "X": list(map(float, x_row)),
                "Y": list(map(float, y_row)),
            })

    # A tidy metadata table (one row per scan)
    df_meta = pd.DataFrame(blocks).drop(columns=["X", "Y"])

    df_coordinates = pd.DataFrame()

    for i, block in enumerate(blocks):
        df_coordinates[f"x_{i}"] = block["X"]
        df_coordinates[f"y_{i}"] = block["Y"]

    return df_meta, df_coordinates

def summarise_metrics(df):
    df = df.copy()
    for col_name in (["x","y"]):
        col_list = df.columns[df.columns.str.startswith(col_name)]
        df[f"mean_{col_name}"] = df[col_list].mean(axis = 1)
        df[f"median_{col_name}"] = df[col_list].median(axis = 1)
    return df

def create_plot(df, filename):
    # Create a larger figure with adjusted DPI for better quality
    fig, ax = plt.subplots(figsize=(16, 10), dpi=120)
    
    # Plot settings
    ax.scatter(df['mean_x'], df['mean_y'], 
               label='Mean values', 
               color='tab:blue', 
               s=15, 
               alpha=1)
    # ax.scatter(df['median_x'], df['median_y'], 
    #            label='Median values', 
    #            color='tab:orange', 
    #            s=8, 
    #            alpha=0.8)
    
    # Formatting
    ax.invert_yaxis()
    # ax.legend(fontsize=12)
    ax.grid(alpha=0.3)
    #ax.set_title(f"Data from {filename}", fontsize=16, pad=20)
    ax.set_xlabel("X Coordinate", fontsize=14)
    ax.set_ylabel("Y Coordinate", fontsize=14)
    
    # Adjust tick label sizes
    ax.tick_params(axis='both', which='major', labelsize=12)
    
    # Add more padding around the plot
    plt.tight_layout()
    
    return fig

def get_tab_title(filename):
    name = Path(filename.name).stem
    name = name.split("_")
    title = f"Pico {name[7][-1]} - {name[1]}/{name[2]}/{name[3]} {name[4]}:{name[5].zfill(2)}"
    return title

def main():
    st.set_page_config(layout="wide", initial_sidebar_state='collapsed')  # Use wide layout mode
    
    st.title("Multi-File Data Visualization")
    st.markdown("---")
    
    # File uploader widget
    uploaded_files = st.file_uploader(
        "Choose data files", 
        accept_multiple_files=True,
        type=['txt', 'csv', 'dat'],  # Specify expected file types

    )
    
    if uploaded_files:
        # Create expandable sidebar with file info
        with st.sidebar.expander("Uploaded Files", expanded=True):
            for file in uploaded_files:
                st.markdown(f"📄 {file.name} ({file.size/1024:.1f} KB)")
        
        # Create a tab for each file
        tabs = st.tabs([f"📊 {get_tab_title(file)}" for file in uploaded_files])
        
        for i, uploaded_file in enumerate(uploaded_files):
            with tabs[i]:
                try:
                    # Get filename without extension
                    filename = Path(uploaded_file.name).stem
                    
                    # Save the uploaded file temporarily
                    with open(uploaded_file.name, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Load and process data
                    df_meta, df_coordinates = load_data(uploaded_file.name)
                    df_summary = summarise_metrics(df_coordinates)
                    
                    # Create two columns for plot and data
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Create and display plot with larger size
                        #st.markdown(f"### {get_tab_title(file)} - Coordinate Plot")
                        fig = create_plot(df_summary, filename)
                        st.pyplot(fig, use_container_width=True)
                        
                    with col2:
                        # Show metadata in an expandable section
                        with st.expander("Metadata", expanded=True):
                            st.dataframe(df_meta.style.set_properties(**{
                                'font-size': '10pt',
                                'text-align': 'left'
                            }))
                        
                        # Show coordinates summary
                        with st.expander("Coordinates Summary", expanded=False):
                            st.dataframe(df_summary.head().style.set_properties(**{
                                'font-size': '10pt',
                                'text-align': 'left'
                            }))
                    
                    # Clean up temporary file
                    Path(uploaded_file.name).unlink()
                    
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")

if __name__ == "__main__":
    main()