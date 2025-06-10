from shiny import App, reactive, ui, render
from maplibre import Map, MapContext, output_maplibregl, render_maplibregl, Layer, LayerType
from maplibre.controls import Marker
from maplibre.sources import GeoJSONSource
from pathlib import Path
import plotly.express as px
import pandas as pd
import json
from shapely.geometry import Polygon, box, MultiPolygon

static_dir = Path(__file__).parent / "static"
geojson_path_on_server = "/area_quemada_2024_4326.geojson"

full_geojson_data = {"type": "FeatureCollection", "features": []}
geojson_df = pd.DataFrame()
try:
    with open(static_dir / "area_quemada_2024_4326.geojson", 'r', encoding='utf-8') as f:
        full_geojson_data = json.load(f)

    features_with_shapely_geom = []
    if full_geojson_data and 'features' in full_geojson_data:
        for f in full_geojson_data['features']:
            props = f.get('properties', {})
            geom = f.get('geometry')

            shapely_geom = None
            if geom:
                if geom['type'] == 'Polygon':
                    try:
                        shapely_geom = Polygon(geom['coordinates'][0])
                    except Exception as e:
                        print(f"Error al crear Shapely Polygon para {props.get('localidad_proxima')}: {e}")
                        shapely_geom = None
                elif geom['type'] == 'MultiPolygon':
                    try:
                        polygons = [Polygon(poly[0]) for poly in geom['coordinates']]
                        shapely_geom = MultiPolygon(polygons)
                    except Exception as e:
                        print(f"Error al crear Shapely MultiPolygon para {props.get('localidad_proxima')}: {e}")
                        shapely_geom = None

            if shapely_geom:
                feature_data = props.copy()
                feature_data['geometry_shapely'] = shapely_geom
                features_with_shapely_geom.append(feature_data)

    geojson_df = pd.DataFrame(features_with_shapely_geom)

    if not geojson_df.empty:
        if 'area_deteccion' in geojson_df.columns:
            geojson_df['area_deteccion'] = pd.to_numeric(geojson_df['area_deteccion'], errors='coerce').fillna(0)
        else:
            print("Advertencia: La columna 'area_deteccion' no se encontró en el GeoJSON cargado o después de procesar.")
    else:
        print("Advertencia: El GeoJSON cargado está vacío o no tiene la clave 'features' válidas para Shapely.")

except FileNotFoundError:
    print(f"Error: El archivo GeoJSON no se encontró en {static_dir / 'area_quemada_2024_4326.geojson'}")
except Exception as e:
    print(f"Error general al cargar o procesar el GeoJSON: {e}")

area_quemada_json_source = GeoJSONSource(data=geojson_path_on_server)
clicked_coords = reactive.Value(None)

# INTERFAZ DE USUARIO
app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.script(src="https://cdn.plot.ly/plotly-2.29.1.min.js"),
        ui.tags.title("Python Maplibre")
    ),
    ui.h3("Áreas Afectadas por Incendios 2024 - Córdoba"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.h4("Área visualizada en el mapa"),
            ui.output_text("info_total_area"),
            ui.output_ui("chart_total_area_html"),
            width="40%"
        ),
        output_maplibregl("map", height=500),
        ui.output_ui("info_click")
    ),
)

# SERVIDOR
def server(input, output, session):
    selected_info_text = reactive.Value("Hacé clic sobre un polígono para ver los datos.")
    total_area_visible = reactive.Value(0.0)
    geojson_in_view = reactive.Value(pd.DataFrame())

    @render_maplibregl
    def map():
        m = Map(center=[-62.36163791, -31.43390571], zoom=10, style="http://127.0.0.1:8000/style.json")
        layer_id = "area-quemada-fill"
        m.add_layer(Layer(
            id=layer_id,
            type=LayerType.FILL,
            source=area_quemada_json_source,
            paint={
                "fill-color": "#e57726",
                "fill-opacity": 0.7
            }
        ))
        m.add_layer(Layer(
            type=LayerType.LINE,
            source=area_quemada_json_source,
            paint={
                "line-color": "#aa0000",
                "line-width": 3
            }
        ))
        coords = clicked_coords.get()
        if coords:
            marker = Marker(lng_lat=coords)
            m.add_marker(marker)

        return m

    @reactive.Effect
    @reactive.event(input.map_feature_clicked)
    async def on_feature_click():
        click_feature = input.map_feature_clicked()
        click_map = input.map_clicked()

        coords = click_map.get('coords', {})
        print(coords)
        lng = coords.get('lng', None)
        lat = coords.get('lat', None)

        if lng is not None and lat is not None:
            clicked_coords.set((lng, lat))

        if click_feature and "props" in click_feature:
            props = click_feature.get("props", {})
            id_area = props.get("id", "N/D")
            area = props.get("area_deteccion", "N/D")
            fecha = props.get("fecha_deteccion", "Sin fecha")
            localidad = props.get("localidad_proxima", "Desconocida")
            departamento = props.get("departamento", "Desconocido")
            sitio_referencia = props.get("sitio_referencia", "N/D")
            cuenca_hidr = props.get("cuenca_hidr", "N/D")
            cobertura1 = props.get("cobertura1", "N/D")
            cobertura2 = props.get("cobertura2", "N/D")
            cobertura3 = props.get("cobertura3", "N/D")
            cobertura4 = props.get("cobertura4", "N/D")
            pend_median = props.get("pend_median", "N/D")
            altitud_mean = props.get("altitud_mean", "N/D")
            orientacion = props.get("orientacion", "N/D")
            grilla = props.get("grilla", "N/D")
            reporte = props.get("reporte", "N/D")

            info_text = (
                f"<h5>🔥Seleccionado:</h5><br>"
                f"- ID: {id_area}<br>"
                f"- Localidad: {localidad}<br>"
                f"- Área Afectada: {area} ha<br>"
                f"- Fecha Detección: {fecha}<br>"
                f"- Departamento: {departamento}<br>"
                f"- Sitio de Referencia: {sitio_referencia}<br>"
                f"- Cuenca Hidrográfica: {cuenca_hidr}<br>"
                f"- Cobertura 1: {cobertura1}<br>"
                f"- Cobertura 2: {cobertura2}<br>"
                f"- Cobertura 3: {cobertura3}<br>"
                f"- Cobertura 4: {cobertura4}<br>"
                f"- Pendiente Media: {pend_median}<br>"
                f"- Altitud Media: {altitud_mean} m<br>"
                f"- Orientación: {orientacion}<br>"
                f"- Grilla: {grilla}<br>"
                f"- Reporte: {reporte}<br>"
            )
            selected_info_text.set(info_text)
        else:
            selected_info_text.set("Hacé clic sobre un polígono para ver los datos.")

    @reactive.Effect
    @reactive.event(input.map_view_state)
    def on_map_view_state():
        view_state = input.map_view_state()
        bounds = view_state.get('bounds')
        if bounds:
            sw = bounds.get('_sw')
            ne = bounds.get('_ne')
            if sw and ne:
                west = sw.get('lng')
                south = sw.get('lat')
                east = ne.get('lng')
                north = ne.get('lat')
                view_bbox = box(west, south, east, north)

                features_in_view_list = []
                for index, row in geojson_df.iterrows():
                    if row['geometry_shapely'] and view_bbox.intersects(row['geometry_shapely']):
                        props_to_add = row.drop('geometry_shapely').to_dict()
                        features_in_view_list.append(props_to_add)

                df_in_view = pd.DataFrame(features_in_view_list)

                if 'area_deteccion' in df_in_view.columns:
                    df_in_view['area_deteccion'] = pd.to_numeric(df_in_view['area_deteccion'], errors='coerce').fillna(0)
                else:
                    print("Advertencia: 'area_deteccion' no está en el DataFrame de características visibles.")
                    df_in_view = pd.DataFrame()

                geojson_in_view.set(df_in_view)

                if not df_in_view.empty and "area_deteccion" in df_in_view.columns and not df_in_view['area_deteccion'].isnull().all():
                    total_area = df_in_view["area_deteccion"].sum()
                    total_area_visible.set(total_area)
                else:
                    total_area_visible.set(0.0)
                    print("No hay características válidas con 'area_deteccion' en el visor o es todo NaN.")
        else:
            total_area_visible.set(0.0)
            geojson_in_view.set(pd.DataFrame())
            print("map_idle: No hay bounds info o geojson_df está vacío.")

    @output
    @render.ui
    def info_click():
        return ui.HTML(selected_info_text.get())

    @output
    @render.text
    def info_total_area():
        return f"Área Total: {total_area_visible.get():.2f} ha"

    @output
    @render.ui
    def chart_total_area_html():
        data = geojson_in_view.get()
        fig = None

        if not data.empty and "area_deteccion" in data.columns and not data['area_deteccion'].isnull().all():
            area_by_localidad = data.groupby("localidad_proxima")["area_deteccion"].sum().reset_index()
            area_by_localidad = area_by_localidad.sort_values(by="area_deteccion", ascending=False)

            fig = px.bar(area_by_localidad,
                         x="localidad_proxima",
                         y="area_deteccion",
                         title="Área por Localidad",
                         labels={"area_deteccion": "Área (ha)", "localidad_proxima": "Localidad"},
                         color_discrete_sequence=px.colors.qualitative.Set1)
            fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=400,
                              xaxis_title=None,
                              yaxis_title="Área (ha)")
        else:
            fig = px.bar(title="No hay áreas quemadas visibles")
            fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=400)

        if fig:
            plot_html = fig.to_html(full_html=False, include_plotlyjs=False)
            return ui.HTML(plot_html)
        return ui.HTML("<div>Error al generar el gráfico.</div>")

app = App(app_ui, server, static_assets=static_dir)

if __name__ == "__main__":
    app.run()
