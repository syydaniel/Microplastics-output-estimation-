import pandas as pd
import geopandas as gpd
import json
import os

# --- Configuration ---
FLUX_DATA_PATH = r"c:\Users\syyda\Desktop\Chapter 4\04_Flux_Analysis\Flux_Data_Modeling.csv"
SHP_BASIN_ATLAS_PATH = r"c:\Users\syyda\Desktop\Chapter 4\BasinATLAS_v10_shp\BasinATLAS_v10_lev12.shp"
OUTPUT_JS_PATH = r"c:\Users\syyda\Desktop\Chapter 4\05_Flux_Uncertainty\all_basins_lev12.js"

# Mass per item conversion factor (from previous analysis)
MASS_PER_ITEM_G = 2.7234e-5

def export_all_lev12():
    print("Loading Flux Data...")
    # Only load necessary columns
    df_flux = pd.read_csv(FLUX_DATA_PATH, usecols=['HYBAS_ID', 'Flux_Linear', 'Natural_Discharge_Upstream'])
    df_flux['HYBAS_ID'] = df_flux['HYBAS_ID'].astype('int64')
    print(f"  - Flux Records: {len(df_flux)}")
    
    print("Loading BasinATLAS Shapefile (for centroids)...")
    # Read only necessary fields
    gdf_atlas = gpd.read_file(SHP_BASIN_ATLAS_PATH, columns=['HYBAS_ID', 'geometry'])
    gdf_atlas['HYBAS_ID'] = gdf_atlas['HYBAS_ID'].astype('int64')
    print(f"  - BasinATLAS Polygons: {len(gdf_atlas)}")
    
    print("Calculating Centroids...")
    gdf_atlas['centroid'] = gdf_atlas.geometry.centroid
    gdf_atlas['lat'] = gdf_atlas['centroid'].y
    gdf_atlas['lon'] = gdf_atlas['centroid'].x
    
    # Drop geometry to save memory
    df_coords = pd.DataFrame({
        'HYBAS_ID': gdf_atlas['HYBAS_ID'],
        'lat': gdf_atlas['lat'],
        'lon': gdf_atlas['lon']
    })
    
    del gdf_atlas
    
    print("Merging Data...")
    df_merged = pd.merge(df_flux, df_coords, on='HYBAS_ID', how='inner')
    print(f"  - Merged Records: {len(df_merged)}")
    
    # Calculate mass flux
    df_merged['flux_baseline'] = df_merged['Flux_Linear'] * MASS_PER_ITEM_G / 1e9  # to kt/yr
    
    # Drop NaN coordinates
    df_merged = df_merged.dropna(subset=['lat', 'lon'])
    print(f"  - Valid Records: {len(df_merged)}")
    
    print("Exporting to JS (minimal format)...")
    output_data = {
        "source": "Level 12 All Basins",
        "total_basins": len(df_merged),
        "total_items_yr": float(df_merged['Flux_Linear'].sum()),
        "total_flux_kt": float(df_merged['flux_baseline'].sum()),
        "basins": []
    }
    
    # Only include essential fields to minimize file size
    for _, row in df_merged.iterrows():
        output_data["basins"].append({
            "id": int(row['HYBAS_ID']),
            "lat": round(float(row['lat']), 4),  # Round to 4 decimals
            "lon": round(float(row['lon']), 4),
            "discharge": round(float(row['Natural_Discharge_Upstream']), 2),
            "flux_items": round(float(row['Flux_Linear']), 2),
            "flux_baseline": round(float(row['flux_baseline']), 6)
        })
    
    js_content = f"window.ALL_BASINS_LEV12 = {json.dumps(output_data)};"
    
    with open(OUTPUT_JS_PATH, 'w') as f:
        f.write(js_content)
    
    file_size_mb = os.path.getsize(OUTPUT_JS_PATH) / (1024 * 1024)
    print(f"Export Complete: {OUTPUT_JS_PATH}")
    print(f"  - File Size: {file_size_mb:.1f} MB")
    print(f"  - Total Basins: {len(df_merged):,}")
    print(f"  - Total Flux: {output_data['total_flux_kt']:.2f} kt/yr")

if __name__ == "__main__":
    export_all_lev12()
