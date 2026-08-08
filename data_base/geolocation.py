import h3
import pandas as pd
import pydeck as pdk
import networkx as nx

PALETTE = [[230, 57, 70],  
            [69, 123, 157],  
            [42, 157, 143],  
            [244, 162, 97],  
            [155, 93, 229]]

AGGR_MAP = {"median": "median",
            "mean": "mean",
            "count": "count",
            "sum": "sum",
            "min": "min",
            "max": "max",
            "std": "std",
            "nunique": "nunique",
            "p90": lambda x: x.quantile(0.90),
            "p10": lambda x: x.quantile(0.10),}


def resolve_attribute(obj, attr_path: str):
    if attr_path== "neighbor_count":
        return len(getattr(obj, "neighbors", []) or [])
    if attr_path== "neighbor_impact":
        neighbors= getattr(obj, "neighbors", []) or []
        scores= [n.impact_score for n in neighbors
                if getattr(n, "impact_score", None) is not None]
        return sum(scores)/len(scores) if scores else 0.0

    curr= obj
    for part in attr_path.split("."):
        if curr is None:
            return 0.0
        curr= getattr(curr, part, None)
    return curr if curr is not None else 0.0


def run_heatmap(city, filter1: str = "re_price_metrics.price",
                filter2: str = "real_estate_metrics.area",):
    
    properties_data= []
    for re in city.available_estates:
        cell_index= re.h3_index
        if not cell_index:
            continue

        val1= resolve_attribute(re, filter1)
        val2= resolve_attribute(re, filter2)
        area_name= resolve_attribute(re, "location.area") or "Default_Area"

        properties_data.append({"h3_index": cell_index,
                "area": area_name, filter1: val1,
                filter2: val2, "neighbor_count": len(re.neighbors)})

    if not properties_data:
        raise ValueError("No valid for-sale properties with valid coordinates found.")

    dfProperties= pd.DataFrame(properties_data)
    user_shade_col= (input(f"Filtro de cor ({filter1}, neighbor_count, etc.): ") or filter1)
    user_shade_aggr= input("Filtragem (median, mean, count...): ") or "median"

    user_height_col= (input(f"Filtro de altura ({filter2}, neighbor_count, etc.): ") or filter2)
    user_height_aggr= input("Filtragem (median, mean, count...): ") or "count"
    metric_shade= [user_shade_col, AGGR_MAP[user_shade_aggr]]
    metric_height= [user_height_col, AGGR_MAP[user_height_aggr]]

    df_hex= (
        dfProperties.groupby(["h3_index", "area"])
        .agg(
            metric_shade=tuple(metric_shade),
            metric_height=tuple(metric_height),
        ).reset_index())

    cell_to_area= df_hex.set_index("h3_index")["area"].to_dict()
    area_graph= nx.Graph()
    area_graph.add_nodes_from(df_hex["area"].unique())

    for cell, area in cell_to_area.items():
        for n in h3.grid_ring(cell, 1):
            if n in cell_to_area and cell_to_area[n] != area:
                area_graph.add_edge(area, cell_to_area[n])

    area_color_map= nx.greedy_color(area_graph)
    df_hex["color_id"]= df_hex["area"].map(area_color_map)

    min_s, max_s= df_hex["metric_shade"].min(), df_hex["metric_shade"].max()
    denom= max_s-min_s if max_s> min_s else 1.0
    shade_factors= 0.35+0.65*((df_hex["metric_shade"]-min_s)/denom)

    df_hex["fill_color"]= [
        [
            int(PALETTE[cid % len(PALETTE)][0] * factor),
            int(PALETTE[cid % len(PALETTE)][1] * factor),
            int(PALETTE[cid % len(PALETTE)][2] * factor),
            210,
        ]
        for cid, factor in zip(df_hex["color_id"], shade_factors)]
    
    df_hex["elevation"]= df_hex["metric_height"] * 50
    lat, lng= h3.cell_to_latlng(df_hex["h3_index"].iloc[0])
    layer= pdk.Layer( "H3HexagonLayer", df_hex, pickable=True, wireframe=False,
                    filled=True, extruded=True, get_hexagon="h3_index",
                    get_fill_color="fill_color", get_elevation="elevation", elevation_scale=1,)

    view_state= pdk.ViewState(latitude=lat, longitude=lng, 
                               zoom=12, pitch=50, bearing=-15)

    deck= pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=
                    {"text": "Area: {area}\nShade Metric: {metric_shade}\nHeight Metric: {metric_height}"})

    deck.to_html("h3_3d_area_heatmap.html")
    return df_hex


def h3_to_geojson(df, hex_col="h3_index"):
    geojson= {"type": "FeatureCollection", "features": []}
    for _, row in df.iterrows():
        boundary = [(lng, lat) for lat, lng in h3.cell_to_boundary(row[hex_col])]
        boundary.append(boundary[0])  

        feature = {"type": "Feature","id": row[hex_col],
                    "geometry": {"type": "Polygon", "coordinates": [boundary]},}
        
        geojson["features"].append(feature)
    return geojson




