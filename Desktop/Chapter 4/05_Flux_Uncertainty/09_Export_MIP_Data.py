import pandas as pd
import json
import os

# --- Configuration ---
MIP_CSV_PATH = r"c:\Users\syyda\Downloads\basins\basins\RSpnt_MIP_10_s1.csv"
DDM30_META_PATH = r"c:\Users\syyda\Downloads\basins\basins\ddm30_MARINAMulti_September2024.csv"
OUTPUT_JS_PATH = r"c:\Users\syyda\Desktop\Chapter 4\05_Flux_Uncertainty\mip_data_ddm30.js"

def export_mip_data():
    print("Loading MIP Data...")
    df_mip = pd.read_csv(MIP_CSV_PATH)
    print(f"  - MIP Records: {len(df_mip)}")
    print(f"  - Columns: {df_mip.columns.tolist()}")
    
    print("Loading DDM30 Metadata...")
    try:
        df_meta = pd.read_csv(DDM30_META_PATH, encoding='latin1')
    except:
        try:
            df_meta = pd.read_csv(DDM30_META_PATH, encoding='utf-8-sig')
        except:
            df_meta = pd.read_csv(DDM30_META_PATH, encoding='utf-8')
    
    # Clean columns
    df_meta.columns = df_meta.columns.str.strip()
    
    # Rename to match
    if 'subbasin' in df_meta.columns:
        df_meta = df_meta.rename(columns={'subbasin': 'Basin_ID'})
    elif 'basin_id' in df_meta.columns:
        df_meta = df_meta.rename(columns={'basin_id': 'Basin_ID'})
    
    if 'lat' in df_meta.columns and 'Lat_mouth' not in df_meta.columns:
        df_meta = df_meta.rename(columns={'lat': 'Lat_mouth', 'lon': 'Lon_mouth'})
    
    if 'name' in df_meta.columns and 'Basin_name' not in df_meta.columns:
        df_meta = df_meta.rename(columns={'name': 'Basin_name'})
    
    # Merge MIP with metadata
    df_merged = pd.merge(df_mip, df_meta[['Basin_ID', 'Basin_name', 'Lat_mouth', 'Lon_mouth']], 
                         left_on='id', right_on='Basin_ID', how='inner')
    
    print(f"  - Merged Records: {len(df_merged)}")
    
    # Calculate total MIP
    total_mip = df_merged['MIPsewt_10_s1'].sum()
    
    print("Exporting to JS...")
    output_data = {
        "source": "MIP Sewage Input (Scenario 10, s1)",
        "total_basins": len(df_merged),
        "total_mip_items": float(total_mip),
        "basins": []
    }
    
    for _, row in df_merged.iterrows():
        output_data["basins"].append({
            "id": int(row['Basin_ID']),
            "name": str(row['Basin_name']) if pd.notna(row['Basin_name']) else "",
            "lat": round(float(row['Lat_mouth']), 4),
            "lon": round(float(row['Lon_mouth']), 4),
            "mip_total": round(float(row['MIPsewt_10_s1']), 2),
            "mip_transport": round(float(row['MIPsewt_trs_10_s1']), 2),
            "mip_precipitation": round(float(row['MIPsewt_pcp_10_s1']), 2),
            "mip_deposition": round(float(row['MIPsewt_dst_10_s1']), 2),
            "mip_land_dry": round(float(row['MIPsewt_ldry_10_s1']), 2)
        })
    
    js_content = f"window.MIP_DATA_DDM30 = {json.dumps(output_data)};"
    
    with open(OUTPUT_JS_PATH, 'w') as f:
        f.write(js_content)
    
    file_size_kb = os.path.getsize(OUTPUT_JS_PATH) / 1024
    print(f"Export Complete: {OUTPUT_JS_PATH}")
    print(f"  - File Size: {file_size_kb:.1f} KB")
    print(f"  - Total Basins: {len(df_merged):,}")
    print(f"  - Total MIP: {total_mip:.2e} items/yr")

if __name__ == "__main__":
    export_mip_data()
