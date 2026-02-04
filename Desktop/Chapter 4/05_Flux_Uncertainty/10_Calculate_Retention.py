import pandas as pd
import json
import os
import numpy as np

# --- Configuration ---
MIP_CSV_PATH = r"c:\Users\syyda\Downloads\basins\basins\RSpnt_MIP_10_s1.csv"
DDM30_FLUX_JS_PATH = r"c:\Users\syyda\Desktop\Chapter 4\05_Flux_Uncertainty\coastal_data_ddm30.js"
DDM30_META_PATH = r"c:\Users\syyda\Downloads\basins\basins\ddm30_MARINAMulti_September2024.csv"
OUTPUT_JS_PATH = r"c:\Users\syyda\Desktop\Chapter 4\05_Flux_Uncertainty\retention_data_ddm30.js"

def calculate_retention():
    print("Loading MIP Data...")
    df_mip = pd.read_csv(MIP_CSV_PATH)
    print(f"  - MIP Records: {len(df_mip)}")
    
    print("Loading DDM30 Flux Data...")
    with open(DDM30_FLUX_JS_PATH, 'r') as f:
        js_content = f.read()
    
    # Extract JSON from JS file
    json_str = js_content.replace('window.COASTAL_DATA_DDM30 = ', '').rstrip(';')
    flux_data = json.loads(json_str)
    
    # Convert to DataFrame
    df_flux = pd.DataFrame(flux_data['basins'])
    print(f"  - Flux Records: {len(df_flux)}")
    
    print("Loading DDM30 Metadata...")
    try:
        df_meta = pd.read_csv(DDM30_META_PATH, encoding='latin1')
    except:
        try:
            df_meta = pd.read_csv(DDM30_META_PATH, encoding='utf-8-sig')
        except:
            df_meta = pd.read_csv(DDM30_META_PATH, encoding='utf-8')
    
    df_meta.columns = df_meta.columns.str.strip()
    if 'subbasin' in df_meta.columns:
        df_meta = df_meta.rename(columns={'subbasin': 'Basin_ID'})
    elif 'basin_id' in df_meta.columns:
        df_meta = df_meta.rename(columns={'basin_id': 'Basin_ID'})
    
    print("Merging Data...")
    # Merge MIP with Flux
    df_merged = pd.merge(df_mip, df_flux, left_on='id', right_on='id', how='inner')
    print(f"  - Merged Records: {len(df_merged)}")
    
    print("Calculating Retention Rates...")
    # Retention Rate = (MIP_Input - Flux_Output) / MIP_Input * 100
    df_merged['mip_input'] = df_merged['MIPsewt_10_s1']
    df_merged['flux_output'] = df_merged['flux_items']
    
    # Calculate retention (handle division by zero)
    df_merged['retention_rate'] = np.where(
        df_merged['mip_input'] > 0,
        ((df_merged['mip_input'] - df_merged['flux_output']) / df_merged['mip_input']) * 100,
        0
    )
    
    # Calculate retained mass (items)
    df_merged['retention_mass'] = df_merged['mip_input'] - df_merged['flux_output']
    
    # Filter out invalid values
    df_merged = df_merged[df_merged['mip_input'] > 0].copy()
    
    # Calculate statistics
    mean_retention = df_merged['retention_rate'].mean()
    median_retention = df_merged['retention_rate'].median()
    p25_retention = df_merged['retention_rate'].quantile(0.25)
    p75_retention = df_merged['retention_rate'].quantile(0.75)
    
    print(f"  - Mean Retention: {mean_retention:.2f}%")
    print(f"  - Median Retention: {median_retention:.2f}%")
    print(f"  - P25-P75: {p25_retention:.2f}% - {p75_retention:.2f}%")
    
    # Create distribution bins
    bins = list(range(0, 101, 10))  # 0, 10, 20, ..., 100
    counts, _ = np.histogram(df_merged['retention_rate'], bins=bins)
    
    print("Exporting to JS...")
    output_data = {
        "source": "DDM30 Retention Rate Analysis",
        "total_basins": len(df_merged),
        "mean_retention": round(float(mean_retention), 2),
        "median_retention": round(float(median_retention), 2),
        "p25_retention": round(float(p25_retention), 2),
        "p75_retention": round(float(p75_retention), 2),
        "total_mip_input": float(df_merged['mip_input'].sum()),
        "total_flux_output": float(df_merged['flux_output'].sum()),
        "total_retained": float(df_merged['retention_mass'].sum()),
        "basins": [],
        "distribution": {
            "bins": bins,
            "counts": counts.tolist()
        }
    }
    
    for _, row in df_merged.iterrows():
        output_data["basins"].append({
            "id": int(row['id']),
            "lat": round(float(row['lat']), 4),
            "lon": round(float(row['lon']), 4),
            "mip_input": round(float(row['mip_input']), 2),
            "flux_output": round(float(row['flux_output']), 2),
            "retention_rate": round(float(row['retention_rate']), 2),
            "retention_mass": round(float(row['retention_mass']), 2)
        })
    
    js_content = f"window.RETENTION_DATA_DDM30 = {json.dumps(output_data)};"
    
    with open(OUTPUT_JS_PATH, 'w') as f:
        f.write(js_content)
    
    file_size_kb = os.path.getsize(OUTPUT_JS_PATH) / 1024
    print(f"Export Complete: {OUTPUT_JS_PATH}")
    print(f"  - File Size: {file_size_kb:.1f} KB")
    print(f"  - Total Basins: {len(df_merged):,}")
    print(f"  - Global Retention: {((output_data['total_mip_input'] - output_data['total_flux_output']) / output_data['total_mip_input'] * 100):.2f}%")

if __name__ == "__main__":
    calculate_retention()
