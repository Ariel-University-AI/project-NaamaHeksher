import ezdxf
from ezdxf.addons import geo
import geopandas as gpd
import fiona

# חובה להדליק את התמיכה של fiona בייצוא ל-KML
fiona.drvsupport.supported_drivers['KML'] = 'rw'

def dxf_layer_to_kml(dxf_path, kml_path, layer_name="M1200"):
    print(f"קורא את הקובץ: {dxf_path}...")
    try:
        # טעינת קובץ ה-DXF
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        print(f"שגיאה בקריאת הקובץ: {e}")
        return

    msp = doc.modelspace()
    
    # סינון: שולף רק את הישויות ששייכות לשכבה הספציפית
    entities = [e for e in msp if e.dxf.layer == layer_name]
    
    if not entities:
        print(f"❌ לא נמצאו אלמנטים בשכבה '{layer_name}'.")
        return
        
    print(f"נמצאו {len(entities)} אלמנטים בשכבה '{layer_name}'. מתחיל בהמרה...")
    
    # המרת הישויות של ezdxf למבנה גאומטרי
    mapping = geo.proxy(entities)
    
    # טעינת הגאומטריות לתוך GeoPandas
    gdf = gpd.GeoDataFrame.from_features(mapping.__geo_interface__["features"])
    
    # הוספת שם השכבה
    gdf['Name'] = layer_name  
    
    # המרת קואורדינטות (ITM ל-WGS84)
    gdf.set_crs(epsg=2039, inplace=True, allow_override=True)
    print("ממיר קואורדינטות מרשת ישראל (ITM) לפורמט גלובלי (WGS84)...")
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    
    # שמירה ל-KML
    gdf_wgs84.to_file(kml_path, driver='KML')
    print(f"✅ הקובץ הומר בהצלחה ונשמר בנתיב: {kml_path}")

if __name__ == "__main__":
    # ==========================================
    # 1. הכנס כאן את הנתיב לקובץ ה-DXF שלך:
    # ==========================================
    dxf_file_path = r"C:\Users\HOME\Desktop\אלי ספרא\data\your_file.dxf" 
    
    # ==========================================
    # 2. הכנס כאן את השם שבו תרצה לשמור את הקובץ (הנתיב המלא):
    # ==========================================
    kml_output_path = r"C:\Users\HOME\Desktop\אלי ספרא\data\Layer_M1200.kml"         

    dxf_layer_to_kml(dxf_file_path, kml_output_path, layer_name="M1200")
