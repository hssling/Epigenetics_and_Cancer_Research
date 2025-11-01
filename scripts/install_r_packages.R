#' Install R package dependencies required for the living review pipeline.
required_packages <- c(
  "tidyverse",
  "meta",
  "DiagrammeR",
  "DiagrammeRsvg",
  "rsvg",
  "htmlwidgets",
  "readr",
  "dplyr",
  "stringr",
  "scales"
)

missing <- setdiff(required_packages, rownames(installed.packages()))

if (length(missing) > 0) {
  message("Installing missing packages: ", paste(missing, collapse = ", "))
  install.packages(missing, repos = "https://cran.rstudio.com/")
} else {
  message("All required packages already installed.")
}
