# exercise 1: used shiny express
from shiny import reactive
from shiny.express import input, render, ui, expressify
import pandas as pd
import io

# Data Cleaner that enables simple data pre-processing
# use only shiny express, instead of shiny core
# shiny run --reload --launch-browser --port 0 "04\a4_ex1\app.py"

###############################################################################

# Use reactive values to manage the internal state of the data - raw and cleaned data
raw_data = reactive.value(None)
cleaned_data = reactive.value(pd.DataFrame())

###############################################################################

# UI
# sidebar layout that contains a sidebar and a pill navset that in turn contains the two navpanels for Data and Analysis
# shiny express style: sidebar = ui.navset_pill(), instead of ui.page_sidebar()

ui.h1("Data Cleaner")

# navset (Data, Analysis)

# Error: TypeError: nav_panel() takes 1 positional argument but 12 were given
# even if we combine them ui.div(), the error still occurs
ui.navset_pill(
    ui.nav_panel("Data",
        ui.input_file("file_upload", "Upload CSV", accept=".csv"),
        ui.input_action_button("reset_button", "Reset", class_="btn-danger"),
        ui.input_action_button("clean_button", "Clean", class_="btn-success"),
        ui.hr(),
        ui.input_selectize("drop_columns", "Columns to drop", choices=[], multiple=True),
        ui.input_radio_buttons("missing", "Missing value handling",
            choices=["No change", "Replace with 0", "Replace with mean", "Replace with median", "Drop rows"],
            selected="No change"
        ),
        ui.input_selectize("transform_columns", "Columns to transform", choices=[], multiple=True),
        ui.input_radio_buttons("transform_type", "Transformation type",
            choices=["None", "Normalize", "Standardize"],
            selected="None"
        ),
        ui.input_dark_mode(id="myDarkMode", value=False),
        ui.hr(),
        ui.h4("Current Data")
    ),
    ui.nav_panel("Analysis",
        ui.input_action_button("analyze_button", "Analyze")
    )
)




###############################################################################
# Functions

# File Upload
@reactive.effect
@reactive.event(input.file_upload)
def load_data():
    # load CSV
    try:
        file_info = input.file_upload()
        if not file_info: return #if user didn't upload a file -> no tasks

        file = file_info[0]
        df = pd.read_csv(file["datapath"])

        # save raw and cleaned data
        raw_data.set(df)
        cleaned_data.set(df.copy())

        # columns list (all, numeric)
        all_columns = df.columns.tolist()
        numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
        
        # update dropdowns
        ui.update_selectize("drop_columns", choices=all_columns)
        ui.update_selectize("transform_columns", choices=numeric_columns)

    # handle errors
    except Exception as e:
        ui.notification_show(f"Error loading file: {e}", type="error", duration=5)

###############################################################################
# Analyse missing values
@render.data_frame
@reactive.event(input.analyze_button)
def analysis_output():
    df = cleaned_data.get()
    if df is None or df.empty: return pd.DataFrame() # return empty df if no dataset is loaded or empty

    # results shown in df sorted by number of missing values in descending order
    missing = df.isnull().sum() # missing values per column
    result = (missing[missing > 0] # filter only columns with at least one missing value
              .sort_values(ascending=False) # in descending order
              .reset_index().rename(columns={"index": "Column", 0: "Missing Values"})) #name columns
    
    return result


###############################################################################
# Data Output
# display the current data
@render.data_frame
def data_output():
    df = cleaned_data.get()
    return df if df is not None else pd.DataFrame()


###############################################################################
# Clean
@reactive.effect
@reactive.event(input.clean_button)
def clean_data():
    df = cleaned_data.get()
    if df is None or df.empty: return # should do nothing if no dataset is loaded

    # 1. drop selected columns
    drop_cols = input.drop_columns()
    df = df.drop(columns= [col for col in drop_cols if col in df.columns], errors="ignore") # e.g. transformation is just ignored for the deleted columns

    # 2. choose how to handle missing values
    missing_opt = input.missing()
    if missing_opt == "Replace with 0":
        df.fillna(0, inplace=True)
    elif missing_opt == "Replace with mean":
        for col in df.select_dtypes(include=["number"]).columns:
            df[col].fillna(df[col].mean(), inplace=True)
    elif missing_opt == "Replace with median":
        for col in df.select_dtypes(include=["number"]).columns:
            df[col].fillna(df[col].median(), inplace=True)
    elif missing_opt == "Drop rows":
        df.dropna(inplace=True)
    
    # 3. transformations of columns (normalize, standardize)
    transform_cols = input.transform_columns()

    if input.transform_type() == "Normalize": # 0-1
        for col in transform_cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
    elif input.transform_type() == "Standardize": # mean=0, std=1
        for col in transform_cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                df[col] = (df[col] - df[col].mean()) / df[col].std()

    # update the cleaned_data
    cleaned_data.set(df)

###############################################################################
# Download cleaned data
@render.download(filename="cleaned_data.csv", label="Download cleaned data")
def download_button():
    df = cleaned_data.get()
    with io.StringIO() as f:
        df.to_csv(f, index=False)
        yield f.getvalue()

###############################################################################
# Reset
@reactive.effect
@reactive.event(input.reset_button)
def reset():
    if raw_data.get() is None: return # should do nothing if no dataset is loaded

    # restore the original uploaded data
    cleaned_data.set(raw_data.get().copy())

    # columns list (all, numeric) - clear all modifications
    all_columns = raw_data.get().columns.tolist()
    numeric_columns = raw_data.get().select_dtypes(include=["number"]).columns.tolist()

    # reset UI
    ui.update_selectize("drop_columns", choices=all_columns, selected=[])
    ui.update_selectize("transform_columns", choices=numeric_columns, selected=[])
    ui.update_radio_buttons("missing", selected="No change")
    ui.update_radio_buttons("transform_type", selected="None")

expressify()