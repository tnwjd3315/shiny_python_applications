# exercise2: used shiny core

from shiny import App, ui, render, reactive
import pandas as pd
import plotly.express as px

# CO2 Dashbaord app that allows to analyse CO2 emissions for the countries of the world
# shiny run --reload --launch-browser --port 0 "04\a4_ex2\app.py"

###############################################################################

# reactive state container
data = reactive.value(None) #start with None, after load_and_prepare_data() change into df
country_list = reactive.value([]) #dynamic list of countries - ui.update_select()
year_min = reactive.value(1750)
year_max = reactive.value(2020)

# defined outside the server function -> can be reused & updated
# hold the changable values & update them by using ui.update_select() and ui.update_slider()

###############################################################################

# UI
app_ui = ui.page_navbar(

    # 1. time series analysis
    ui.nav_panel(
        "Country – Co2 Time Series",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_select("country", "Choose a country", choices=[], selected="Austria"),
                ui.input_slider("window", "Rolling mean (years)", min=1, max=20, value=5) #slider goes from 1 to 20 with 5 as default
            ),
            ui.output_ui("lineplot")  # plotly will be rendered as HTML
        )
    ),

    # 2. world map per year
    ui.nav_panel(
        "World Map – CO2 Emissions per Country",
        ui.layout_sidebar(
            ui.sidebar(ui.input_slider("year_slider", "Year", min=1900, max=2020, value=2007, step=1)),
            ui.output_ui("mapplot")  # plotly will be rendered as HTML
        )
    ),
    title="CO2 Dashboard"
)

###############################################################################

# Server

def server(input, output, session):

    # co2 data
    @reactive.effect
    def load_and_prepare_data():
        url = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
        df = pd.read_csv(url, usecols=["country", "iso_code", "year", "co2"]) #necessary columns
        df["co2"] = pd.to_numeric(df["co2"], errors="coerce") # coerce co2 to numeric
        df = df.dropna(subset=["iso_code", "co2"]) # drop NaN values using subset
        df = df[(df["co2"] > 0) & (df["iso_code"].str.len() == 3)] # filter the data
        data.set(df) #store cleaned data in reactive state

        # update the select input and slider (dynamic)
        country_list.set(sorted(df["country"].unique())) #ensure to contains unique countries
        ui.update_select("country", choices=country_list.get(), selected="Austria")

        year_min.set(int(df["year"].min()))
        year_max.set(int(df["year"].max()))
        ui.update_slider("year_slider", min=year_min.get(), max=year_max.get(),
                         value=2007 if 2007 in df["year"].values else year_min.get())

    # 1. time series plot output
    @output
    @render.ui
    def lineplot():
        df = data.get()
        if df is None: return "No data"

        df_country = df[df["country"] == input.country()]
        df_country = df_country.sort_values("year")

        # rolling mean over a window that is set by the slider
        df_country["rolling_mean"] = df_country["co2"].rolling(window=input.window(), min_periods=1).mean()

        fig = px.line(df_country, x="year", y="co2", labels={"co2": "CO2 [million tons]"},
                      title=f"CO2 emissions — {input.country()}")
        fig.add_scatter(x=df_country["year"], y=df_country["rolling_mean"],
                        mode="lines", name=f"{input.window()}-year mean") # smoothed line
        
        # hover mode - x unified, using update_layout()
        fig.update_layout(hovermode="x unified")

        # plotly is converted to html and rendered via ui.output_ui()
        return ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False))

    # 2. world map plot output
    @output
    @render.ui
    def mapplot():
        df = data.get()
        if df is None: return "No data"

        df_year = df[df["year"] == input.year_slider()]

        # plotly.express::choropleth()
        fig = px.choropleth(
            df_year, locations="iso_code", color="co2",
            hover_name="country", hover_data=["iso_code", "co2"], #primary info is country name
            color_continuous_scale="Reds", #color scale "Reds"
            labels={"co2": "CO2 (million t)"},
            title=f"CO2 emissions worldwide {input.year_slider()}"
        )
        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0}) # top margine 40

        # render chropleth as html
        return ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False))

# unfortunately shiny core is used
app = App(app_ui, server)
