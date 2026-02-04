import json

# --- Configuration ---
INPUT_JS_PATH = r"c:\Users\syyda\Desktop\Chapter 4\05_Flux_Uncertainty\coastal_data_ddm30.js"
OUTPUT_JS_PATH = r"c:\Users\syyda\Desktop\Chapter 4\05_Flux_Uncertainty\coastal_ddm30.js"

def filter_coastal_ddm30():
    print("Loading DDM30 All Basins Data...")
    
    # Read the JS file and extract JSON
    with open(INPUT_JS_PATH, 'r') as f:
        js_content = f.read()
    
    # Extract JSON from "window.COASTAL_DATA_DDM30 = {...};"
    json_str = js_content.replace('window.COASTAL_DATA_DDM30 = ', '').rstrip(';')
    data = json.loads(json_str)
    
    print(f"  - Total DDM30 Basins: {data['total_basins']}")
    
    # Filter for coastal basins only (mouth == 1)
    # Note: The current data doesn't have 'mouth' field, so we need to load from CSV
    print("Loading DDM30 Metadata for mouth filter...")
    import pandas as pd
    
    try:
        df_meta = pd.read_csv(r"c:\Users\syyda\Downloads\basins\basins\ddm30_MARINAMulti_September2024.csv", 
                              encoding='latin1')
    except:
        df_meta = pd.read_csv(r"c:\Users\syyda\Downloads\basins\basins\ddm30_MARINAMulti_September2024.csv", 
                              encoding='utf-8-sig')
    
    # Clean column names
    df_meta.columns = df_meta.columns.str.strip()
    
    # Rename to match
    if 'subbasin' in df_meta.columns:
        df_meta = df_meta.rename(columns={'subbasin': 'Basin_ID'})
    elif 'basin_id' in df_meta.columns:
        df_meta = df_meta.rename(columns={'basin_id': 'Basin_ID'})
    
    # Filter for mouth == 1
    coastal_ids = set(df_meta[df_meta['mouth'] == 1]['Basin_ID'].values)
    print(f"  - Coastal Basins (mouth==1): {len(coastal_ids)}")
    
    # Filter basins
    coastal_basins = [b for b in data['basins'] if b['id'] in coastal_ids]
    
    print(f"  - Matched Coastal Basins: {len(coastal_basins)}")
    
    # Create output data
    output_data = {
        "source": "DDM30 Coastal Basins (mouth==1)",
        "total_basins": len(coastal_basins),
        "total_items_yr": sum(b['flux_items'] for b in coastal_basins),
        "total_flux_kt": sum(b['flux_baseline'] for b in coastal_basins),
        "basins": coastal_basins
    }
    
    # Export
    js_content = f"window.COASTAL_DDM30 = {json.dumps(output_data)};"
    
    with open(OUTPUT_JS_PATH, 'w') as f:
        f.write(js_content)
    
    import os
    file_size_kb = os.path.getsize(OUTPUT_JS_PATH) / 1024
    print(f"Export Complete: {OUTPUT_JS_PATH}")
    print(f"  - File Size: {file_size_kb:.1f} KB")
    print(f"  - Total Coastal Basins: {len(coastal_basins):,}")
    print(f"  - Total Flux: {output_data['total_flux_kt']:.2f} kt/yr")

if __name__ == "__main__":
    filter_coastal_ddm30()
