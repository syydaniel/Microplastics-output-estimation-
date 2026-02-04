import geopandas as gpd
import pandas as pd
import numpy as np
import json
import os

# --- Configuration ---
# Use the detected python path if needed in executing, but this is the script content.
SHP_BASIN_ATLAS_PATH = r"c:\Users\syyda\Desktop\Chapter 4\BasinATLAS_v10_shp\BasinATLAS_v10_lev12.shp"
SHP_DDM30_PATH = r"c:\Users\syyda\Downloads\basins\basins\basins_joined.shp"
CSV_DDM30_PATH = r"c:\Users\syyda\Downloads\basins\basins\ddm30_MARINAMulti_September2024.csv"
FLUX_DATA_PATH = r"c:\Users\syyda\Desktop\Chapter 4\04_Flux_Analysis\Flux_Data_Modeling.csv"
OUTPUT_JS_PATH = r"c:\Users\syyda\Desktop\Chapter 4\05_Flux_Uncertainty\coastal_data_ddm30.js"

def load_and_process():
    print("Loading Data...")
    
    # 1. Load Flux Data (Model Results) n=900k
    print(f"Reading Flux Data: {FLUX_DATA_PATH}")
    # We need HYBAS_ID, Flux_Linear (Items?), Natural_Discharge_Upstream
    use_cols = ['HYBAS_ID', 'Flux_Linear', 'Natural_Discharge_Upstream']
    # Check if headers exist, read first row to confirm
    df_flux = pd.read_csv(FLUX_DATA_PATH)
    
    # Ensure HYBAS_ID is int64
    df_flux['HYBAS_ID'] = df_flux['HYBAS_ID'].astype('int64')
    print(f"  - Flux Records: {len(df_flux)}")

    # 2. Load BasinATLAS Geometry (n=huge)
    # We need to attach geometry to df_flux based on HYBAS_ID
    print(f"Reading BasinATLAS SHP (This may take a moment): {SHP_BASIN_ATLAS_PATH}")
    # Read only geometry and HYBAS_ID to save memory
    gdf_atlas = gpd.read_file(SHP_BASIN_ATLAS_PATH, include_fields=['HYBAS_ID', 'geometry']) 
    # Note: 'include_fields' might not be supported in older fiona/gpd versions, 
    # but gpd.read_file reads all. We'll filter columns after read if needed.
    
    gdf_atlas['HYBAS_ID'] = gdf_atlas['HYBAS_ID'].astype('int64')
    print(f"  - BasinATLAS Polygons: {len(gdf_atlas)}")
    
    # 3. Merge Flux Data with Geometry
    print("Merging Flux Data with Geometry...")
    # Inner join: Only map basins we have flux data for
    gdf_flux = gdf_atlas.merge(df_flux, on='HYBAS_ID', how='inner')
    print(f"  - Mapped Flux Basins: {len(gdf_flux)}")
    
    # Free up memory
    del gdf_atlas
    del df_flux
    
    # 4. Convert to Centroids for Point-in-Polygon check?
    # Or keep as polygons for potential intersection?
    # Centroids are faster for "Assignment".
    print("Calculating Centroids...")
    gdf_flux['centroid'] = gdf_flux.geometry.centroid
    gdf_flux = gdf_flux.set_geometry('centroid') # Set active geometry to centroid
    # drop polygon geometry to save memory if verified
    # gdf_flux = gdf_flux.drop(columns=['geometry']) 
    
    # 5. Load DDM30 Basins
    print(f"Reading DDM30 SHP: {SHP_DDM30_PATH}")
    gdf_ddm30 = gpd.read_file(SHP_DDM30_PATH)
    # Rename columns to match DDM30 CSV schema
    gdf_ddm30 = gdf_ddm30.rename(columns={'subbasn': 'Basin_ID', 'name': 'Basin_name'})
    
    if gdf_ddm30.crs and gdf_ddm30.crs.to_epsg() != 4326:
        gdf_ddm30 = gdf_ddm30.to_crs(epsg=4326)
        
    # Ensure Flux Data is CRS 4326
    if gdf_flux.crs and gdf_flux.crs.to_epsg() != 4326:
        gdf_flux = gdf_flux.to_crs(epsg=4326)

    # 6. Spatial Join: Assign Lev12 Subbasins to DDM30 Basins
    print("Performing Spatial Join (Level 12 Centroids -> DDM30 Polygons)...")
    # outcome: each Lev12 ID will have a DDM30 Basin_ID
    joined = gpd.sjoin(gdf_flux, gdf_ddm30[['Basin_ID', 'Basin_name', 'geometry']], how="inner", predicate="within")
    print(f"  - Joined Records: {len(joined)}")
    
    # 7. Aggregate: Sum all Level 12 basins within each DDM30 basin
    print("Aggregating to DDM30 (Summing all basins within each DDM30 polygon)...")
    
    # Group by Basin_ID and sum the flux values
    aggregated = joined.groupby('Basin_ID').agg({
        'Flux_Linear': 'sum',  # Sum all items flux
        'Natural_Discharge_Upstream': 'sum',  # Sum discharge (or could use max)
        'Basin_name': 'first',  # Keep first name
        'centroid': 'first'  # Keep first centroid (will use DDM30 mouth coords later)
    }).reset_index()
    
    # Calculate aggregated coordinates (use centroid of first basin, but will override with DDM30 mouth)
    aggregated['lat'] = aggregated['centroid'].apply(lambda p: p.y if p else None)
    aggregated['lon'] = aggregated['centroid'].apply(lambda p: p.x if p else None)
    
    print(f"  - Aggregated DDM30 Basins: {len(aggregated)}")
    print(f"  - Total Level 12 basins used: {len(joined)}")
    print(f"  - Average basins per DDM30: {len(joined)/len(aggregated):.1f}")
    
    # 8. Load DDM30 CSV for Filters and correct Mouth Coordinates
    print(f"Reading DDM30 Metadata: {CSV_DDM30_PATH}")
    try:
        df_ddm30_meta = pd.read_csv(CSV_DDM30_PATH, encoding='latin1')
    except:
        try:
            df_ddm30_meta = pd.read_csv(CSV_DDM30_PATH, encoding='utf-8-sig')
        except:
            df_ddm30_meta = pd.read_csv(CSV_DDM30_PATH, encoding='utf-8')
    
    import sys
    print("Aggregated Columns:", aggregated.columns.tolist())
    sys.stdout.flush()
    
    # Clean CSV columns
    df_ddm30_meta.columns = df_ddm30_meta.columns.str.strip()
    print("Meta Columns (Cleaned):", df_ddm30_meta.columns.tolist())
    sys.stdout.flush()
    
    # Rename CSV columns to match key
    if 'Basin_ID' not in df_ddm30_meta.columns:
        if 'subbasin' in df_ddm30_meta.columns:
            print("Renaming 'subbasin' to 'Basin_ID'")
            df_ddm30_meta = df_ddm30_meta.rename(columns={'subbasin': 'Basin_ID'})
        elif 'basin_id' in df_ddm30_meta.columns:
            print("Renaming 'basin_id' to 'Basin_ID'")
            df_ddm30_meta = df_ddm30_meta.rename(columns={'basin_id': 'Basin_ID'})
    
    # Also handle 'Lat_mouth'/'Lon_mouth' if they are 'lat'/'lon'
    if 'Lat_mouth' not in df_ddm30_meta.columns and 'lat' in df_ddm30_meta.columns:
        df_ddm30_meta = df_ddm30_meta.rename(columns={'lat': 'Lat_mouth', 'lon': 'Lon_mouth'})
        
    # Also 'Basin_name'
    if 'Basin_name' not in df_ddm30_meta.columns and 'name' in df_ddm30_meta.columns:
        df_ddm30_meta = df_ddm30_meta.rename(columns={'name': 'Basin_name'})

    # Merge aggregated flux with DDM30 metadata (Coordinates, Filtering info)
    # We prefer Lat_mouth/Lon_mouth from DDM30 meta over the Lev12 centroid
    final_df = pd.merge(aggregated, df_ddm30_meta, on='Basin_ID', how='inner', suffixes=('_lev12', '_ddm30'))
    
    # 9. Apply Filters
    # "filter should also be appied by using ddm30 related file"
    # Filter by Include_Flag if present
    if 'Include_Flag' in final_df.columns:
        print("Filtering by Include_Flag == 1...")
        final_df = final_df[final_df['Include_Flag'] == 1]
    
    print(f"  - Final Count: {len(final_df)}")
    
    # 10. Export
    print("Exporting to JS...")
    
    output_data = {
        "source": "DDM30 Aggregated (Sum of all Lev12 basins within each DDM30)",
        "total_basins": len(final_df),
        "total_items_yr": final_df['Flux_Linear'].sum(),
        "basins": []
    }
    
    for _, row in final_df.iterrows():
        # Coordinates: Use DDM30 reported Mouth coordinates
        lat = row.get('Lat_mouth', row.get('Lat_mouth_ddm30', 0))
        lon = row.get('Lon_mouth', row.get('Lon_mouth_ddm30', 0))
        
        # Flux: The Flux_Linear from the selected Level 12 outlet
        flux_val = row['Flux_Linear'] # Items/yr
        discharge_val = row['Natural_Discharge_Upstream'] # From Lev12 model
        
        # Calculate Mass Flux (kt/yr)
        # Factor from previous data: 19.148 kt / 703.1e12 items = 2.7234e-5 mg/item ?? 
        # 19.148 * 10^9 mg / 703.1 * 10^12 = 0.027 mg. 
        # Wait: 1 kt = 1e9 g. 19 kt = 19e9 g. 
        # 19e9 g / 703e12 items = 2.7e-5 g/item = 0.027 mg/item.
        mass_per_item_g = 2.7234e-5
        flux_mass_val = flux_val * mass_per_item_g / 1e9 # to kt
        
        # Name
        name = row.get('Basin_name_ddm30', row.get('Basin_name', f"Basin {row['Basin_ID']}"))
        
        if pd.isna(lat) or pd.isna(lon):
            continue
            
        output_data["basins"].append({
            "id": int(row['Basin_ID']),
            "name": str(name),
            "lat": float(lat),
            "lon": float(lon),
            "discharge": float(discharge_val),
            "flux_items": float(flux_val),
            "flux_baseline": float(flux_mass_val),
            # Optional: DDM30 also has 'Dis_m3s' (observed/modeled). 
            # We provide our model's discharge for consistency with Flux calculation.
        })
        
    output_data["total_flux_kt"] = sum(b['flux_baseline'] for b in output_data["basins"])
    
    js_content = f"window.COASTAL_DATA_DDM30 = {json.dumps(output_data)};"
    
    with open(OUTPUT_JS_PATH, 'w') as f:
        f.write(js_content)
        
    print(f"Write successful: {OUTPUT_JS_PATH}")

if __name__ == "__main__":
    load_and_process()
