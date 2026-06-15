from src.pages.comparative import render as render_comparative_page
from src.pages.eda import render as render_eda_page
from src.pages.experimental_design import render as render_experimental_page
from src.pages.modeling import render as render_modeling_page
from src.pages.pipeline import render as render_pipeline_page
from src.pages.regression import render as render_regression_page
from src.pages.spatial import render as render_spatial_page
from src.pages.timeseries import render as render_timeseries_page
from src.pages.upload import render as render_upload_page

PAGE_RENDERERS = {
    "upload": render_upload_page,
    "pipeline": render_pipeline_page,
    "eda": render_eda_page,
    "regression": render_regression_page,
    "modeling": render_modeling_page,
    "spatial": render_spatial_page,
    "timeseries": render_timeseries_page,
    "comparative": render_comparative_page,
    "experimental": render_experimental_page,
}

__all__ = ["PAGE_RENDERERS"]
