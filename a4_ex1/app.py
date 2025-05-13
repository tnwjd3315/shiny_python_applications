# exercise1: used shiny core

from shiny import App, ui, render, reactive
import pandas as pd
import io

# Data Cleaner that enables simple data pre-processing
# shiny run --reload --launch-browser --port 0 "04\a4_ex1\app.py"

###############################################################################

# Use reactive values to manage the internal state of the data - raw and cleaned data
raw_data = reactive.value(None)
cleaned_data = reactive.value(pd.DataFrame())

###############################################################################

# UI
# sidebar layout that contains a sidebar and a pill navset that in turn contains the two navpanels for Data and Analysis

app_ui = ui.page_navbar(
    ui.nav_panel("Data",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_file("file_upload", "Upload CSV file", accept=[".csv"]),
                ui.input_action_button("analyze_button", "Analyze"),
                ui.hr(),

                ui.input_selectize("drop_columns", "Remove Columns", choices=[], multiple=True),
                ui.input_select("missing", "With NaNs:", 
                                choices=["No change", "Replace with 0", "Replace with mean", "Replace with median", "Drop rows"],
                                selected="No change"),
                ui.input_selectize("transform_columns", "Columns to transform", choices=[], multiple=True),
                ui.input_select("transform_type", "Transform Strategy:",
                                choices=["No change", "Normalize", "Standardize"],
                                selected="No change"),
                ui.hr(),

                ui.input_action_button("clean_button", "Clean"),
                ui.download_button("download_button", "Download Cleaned Data"),
                ui.input_action_button("reset_button", "Reset"),
                ui.input_dark_mode()
            ),
            ui.output_data_frame("data_output")
        )
    ),
    ui.nav_panel("Analysis",
        ui.output_data_frame("analysis_output")
    ),
    title="Data Cleaner"
)

###############################################################################

# Functions

def server(input, output, session):

    # File Upload
    @reactive.effect
    @reactive.event(input.file_upload)
    def load_data():
        try:
            file = input.file_upload()[0]
            df = pd.read_csv(file["datapath"])
            raw_data.set(df)
            cleaned_data.set(df.copy())

            all_cols = df.columns.tolist()
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            ui.update_selectize("drop_columns", choices=all_cols)
            ui.update_selectize("transform_columns", choices=numeric_cols)
        except Exception as e:
            ui.notification_show(f"Error loading file: {e}", type="error", duration=5)

    # display the current data
    @render.data_frame
    def data_output():
        df = cleaned_data.get()
        return df if df is not None else pd.DataFrame()


    # Analyse missing values
    @render.data_frame
    @reactive.event(input.analyze_button)
    def analysis_output():
        df = cleaned_data.get()
        if df is None or df.empty:
            return pd.DataFrame()
        return pd.DataFrame({
            "Column": df.columns,
            "Missing values": df.isnull().sum(),
            "Data type": df.dtypes.astype(str),
            "Nr. of unique values": [df[col].nunique() for col in df.columns]
        })

    # Clean
    @reactive.effect
    @reactive.event(input.clean_button)
    def clean_data():
        df = cleaned_data.get()
        if df is None or df.empty: return
        df = df.copy()

        for col in input.drop_columns():
            if col in df.columns:
                df.drop(columns=col, inplace=True)

        missing = input.missing()
        if missing == "Replace with 0":
            df.fillna(0, inplace=True)
        elif missing == "Replace with mean":
            for col in df.select_dtypes(include="number").columns:
                df[col].fillna(df[col].mean(), inplace=True)
        elif missing == "Replace with median":
            for col in df.select_dtypes(include="number").columns:
                df[col].fillna(df[col].median(), inplace=True)
        elif missing == "Drop rows":
            df.dropna(inplace=True)

        for col in input.transform_columns():
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                if input.transform_type() == "Normalize":
                    df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
                elif input.transform_type() == "Standardize":
                    df[col] = (df[col] - df[col].mean()) / df[col].std()

        cleaned_data.set(df)

    # Reset
    @reactive.effect
    @reactive.event(input.reset_button)
    def reset():
        df = raw_data.get()
        if df is not None:
            cleaned_data.set(df.copy())
            ui.update_selectize("drop_columns", choices=df.columns.tolist(), selected=[])
            ui.update_selectize("transform_columns", choices=df.select_dtypes(include="number").columns.tolist(), selected=[])
            ui.update_radio_buttons("missing", selected="No change")
            ui.update_radio_buttons("transform_type", selected="No change")

    # Download cleaned data
    @render.download(filename="cleaned_data.csv")
    def download_button():
        df = cleaned_data.get()
        with io.StringIO() as f:
            df.to_csv(f, index=False)
            yield f.getvalue()

app = App(app_ui, server)
