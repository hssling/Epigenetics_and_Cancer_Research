#!/usr/bin/env Rscript

# ===============================================
# Meta-Analysis for Epigenetics in Public Health & Cancer Prevention
# ===============================================

# Load required packages
required_packages <- c(
  "tidyverse",
  "meta",
  "ggplot2",
  "DiagrammeR",
  "DiagrammeRsvg",
  "rsvg",
  "htmlwidgets",
  "readr",
  "dplyr",
  "stringr"
)

for (pkg in required_packages) {
  if (!require(pkg, character.only = TRUE)) {
    install.packages(pkg, repos = "https://cran.rstudio.com/")
    library(pkg, character.only = TRUE)
  }
}

# Working directory should already be project root
cat("Working directory:", getwd(), "\n")

# Load data
if (!file.exists("data/epigenetic_master_dataset.csv")) {
  stop("Master dataset not found. Please run data extraction first.")
}

data <- read_csv("data/epigenetic_master_dataset.csv", show_col_types = FALSE)

cat("Loaded", nrow(data), "studies for meta-analysis\n")

# ===============================================
# 1. Descriptive Summaries by Exposure Domain
# ===============================================

cat("Generating descriptive summaries...\n")

# Summary by exposure type
exposure_summary <- data %>%
  group_by(exposure_type) %>%
  summarise(
    n_studies = n(),
    mean_effect = mean(epigenetic_effect_size, na.rm = TRUE),
    sd_effect = sd(epigenetic_effect_size, na.rm = TRUE),
    median_population = median(population_size, na.rm = TRUE),
    countries = n_distinct(country)
  )

print(exposure_summary)

# ===============================================
# 2. Meta-Analysis and Network Meta-Analysis (NMA)
# ===============================================

cat("Performing meta-analysis for epigenetic factors in cancer prevention...\n")

# Check if we have enough studies for NMA (at least 3 different interventions)
exposure_types <- unique(data$exposure_type)
cat("Available exposure types:", paste(exposure_types, collapse = ", "), "\n")

comparison_results <- list()

if (length(exposure_types) >= 3) {
  cat("Performing Network Meta-Analysis (NMA) for multiple exposure types...\n")

  # For NMA, we would need the netmeta package
  # This is a simplified version - in practice would use proper NMA methods

  # Calculate effect sizes by exposure type
  nma_data <- data %>%
    group_by(exposure_type) %>%
    summarise(
      n_studies = n(),
      mean_effect = mean(epigenetic_effect_size, na.rm = TRUE),
      se_effect = sd(epigenetic_effect_size, na.rm = TRUE) / sqrt(n()),
      ci_lower = mean_effect - 1.96 * se_effect,
      ci_upper = mean_effect + 1.96 * se_effect
    ) %>%
    filter(n_studies >= 2)  # Need at least 2 studies per intervention

  print("Network Meta-Analysis Summary:")
  print(nma_data)

  # Create comparison matrix (simplified)
  cat("\nIntervention Comparisons:\n")
  for (i in 1:(nrow(nma_data)-1)) {
    for (j in (i+1):nrow(nma_data)) {
      effect_diff <- nma_data$mean_effect[i] - nma_data$mean_effect[j]
      se_diff <- sqrt(nma_data$se_effect[i]^2 + nma_data$se_effect[j]^2)
      z_score <- effect_diff / se_diff
      p_value <- 2 * (1 - pnorm(abs(z_score)))

      cat(sprintf("%s vs %s: MD = %.3f (95%% CI: %.3f to %.3f), p = %.3f\n",
                  nma_data$exposure_type[i], nma_data$exposure_type[j],
                  effect_diff,
                  effect_diff - 1.96*se_diff, effect_diff + 1.96*se_diff,
                  p_value))

      comparison_results[[length(comparison_results) + 1]] <- tibble(
        exposure_a = nma_data$exposure_type[i],
        exposure_b = nma_data$exposure_type[j],
        mean_difference = effect_diff,
        ci_lower = effect_diff - 1.96 * se_diff,
        ci_upper = effect_diff + 1.96 * se_diff,
        p_value = p_value
      )
    }
  }

} else {
  cat("Performing traditional meta-analysis by exposure type...\n")

  # Traditional meta-analysis by exposure type
  for (exp_type in exposure_types) {
    exp_data <- data %>% filter(exposure_type == exp_type)

    if (nrow(exp_data) >= 2) {
      cat("\nMeta-analysis for", exp_type, "exposure:\n")

      # Simple pooled effect (would use proper meta-analysis in practice)
      pooled_effect <- mean(exp_data$epigenetic_effect_size, na.rm = TRUE)
      pooled_se <- sd(exp_data$epigenetic_effect_size, na.rm = TRUE) / sqrt(nrow(exp_data))

      cat(sprintf("Pooled effect: %.3f (95%% CI: %.3f to %.3f)\n",
                  pooled_effect,
                  pooled_effect - 1.96*pooled_se,
                  pooled_effect + 1.96*pooled_se))
    }
  }
}

comparison_df <- if (length(comparison_results) > 0) {
  dplyr::bind_rows(comparison_results)
} else {
  tibble()
}

# SEPT9 specific analysis if available
sept9_data <- data %>%
  filter(str_detect(epigenetic_marker, "SEPT9|sept9") & !is.na(proportion_positive) & !is.na(sample_size))

if (nrow(sept9_data) > 0) {
  cat("\n\nSEPT9 Methylation Meta-Analysis:\n")

  # Meta-analysis using metaprop
  sept9_meta <- metaprop(
    event = round(proportion_positive * sample_size),
    n = sample_size,
    studlab = paste(authors, year, sep = ", "),
    data = sept9_data,
    sm = "PLOGIT",
    method.tau = "ML",
    title = "SEPT9 Methylation in Cancer Prevention"
  )

  # Print results
  print(sept9_meta)

  # Heterogeneity assessment
  cat("Heterogeneity: I² =", round(sept9_meta$I2, 2), "%, τ² =", round(sept9_meta$tau2, 4), ", p =", format.pval(sept9_meta$pval.Q, digits = 3), "\n")

  # ===============================================
  # 3. Generate Figures
  # ===============================================

  # Figure 1: PRISMA Flow Diagram
  cat("Creating PRISMA flow diagram...\n")

  prisma_data <- read_csv("data/prisma_counts.csv", show_col_types = FALSE)

  prisma_counts_named <- setNames(prisma_data$count, prisma_data$stage)
  prisma_reasons_named <- setNames(prisma_data$reason, prisma_data$stage)

  label_with_reason <- function(stage_key) {
    count_val <- prisma_counts_named[[stage_key]]
    if (is.null(count_val) || is.na(count_val)) {
      count_val <- 0
    }
    reason_val <- prisma_reasons_named[[stage_key]]
    reason_text <- if (!is.null(reason_val) && !is.na(reason_val) && nzchar(reason_val)) {
      paste0("\n", reason_val)
    } else {
      ""
    }
    paste0("n = ", count_val, reason_text)
  }

  prisma_labels <- c(
    paste("Records identified", label_with_reason("records_identified"), sep = "\n"),
    paste("Records screened", label_with_reason("records_screened"), sep = "\n"),
    paste("Records excluded", label_with_reason("records_excluded"), sep = "\n"),
    paste("Full-text articles assessed", label_with_reason("full_text_assessed"), sep = "\n"),
    paste("Full-text articles excluded", label_with_reason("full_text_excluded"), sep = "\n"),
    paste("Studies included", label_with_reason("studies_included"), sep = "\n")
  )

  prisma_nodes <- DiagrammeR::create_node_df(
    n = length(prisma_labels),
    label = prisma_labels,
    style = "filled",
    fillcolor = "lightblue",
    shape = "rectangle",
    fontname = "Helvetica",
    fontsize = 10,
    width = 3.5,
    height = 1.2
  )

  prisma_edges <- DiagrammeR::create_edge_df(
    from = c(1, 2, 2, 4, 4),
    to = c(2, 3, 4, 5, 6)
  )

  prisma_graph <- DiagrammeR::create_graph(
    nodes_df = prisma_nodes,
    edges_df = prisma_edges,
    directed = TRUE
  ) |>
    DiagrammeR::add_global_graph_attrs(attr = "layout", value = "dot", attr_type = "graph") |>
    DiagrammeR::add_global_graph_attrs(attr = "rankdir", value = "TB", attr_type = "graph") |>
    DiagrammeR::add_global_graph_attrs(attr = "nodesep", value = "0.5", attr_type = "graph") |>
    DiagrammeR::add_global_graph_attrs(attr = "ranksep", value = "0.75", attr_type = "graph")

  if (requireNamespace("DiagrammeRsvg", quietly = TRUE)) {
    svg_widget <- DiagrammeR::render_graph(prisma_graph)
    svg_content <- DiagrammeRsvg::export_svg(svg_widget)
    writeLines(svg_content, "figures/Figure1_PRISMA_Flow.svg")

    if (requireNamespace("rsvg", quietly = TRUE)) {
      tryCatch(
        {
          rsvg::rsvg_png(
            charToRaw(svg_content),
            file = "figures/Figure1_PRISMA_Flow.png",
            width = 800,
            height = 600
          )
        },
        error = function(e) {
          message("Failed to convert PRISMA SVG to PNG: ", e$message)
        }
      )
    } else {
      message("rsvg package unavailable; saved SVG version of PRISMA diagram.")
    }
  } else {
    html_graph <- DiagrammeR::render_graph(prisma_graph)
    if (requireNamespace("htmlwidgets", quietly = TRUE)) {
      htmlwidgets::saveWidget(
        html_graph,
        file = "figures/Figure1_PRISMA_Flow.html",
        selfcontained = TRUE
      )
      message("DiagrammeRsvg not available; saved HTML version of PRISMA diagram.")
    } else {
      message("DiagrammeRsvg and htmlwidgets not available; unable to save PRISMA diagram.")
    }
  }

  # Figure 2: Forest Plot for SEPT9
  cat("Creating forest plot...\n")

  if (nrow(sept9_data) > 1) {
    png("figures/Figure2_ForestPlot_mSEPT9.png", width = 800, height = 600, res = 300)
    forest(
      sept9_meta,
      layout = "RevMan5",
      pooled.totals = TRUE,
      pooled.events = TRUE
    )
    dev.off()
  } else {
    cat("Creating single-study SEPT9 visualization...\n")
    study_label <- sept9_data %>%
      mutate(
        primary_author = strsplit(authors, ";") %>% purrr::map_chr(~ stringr::str_trim(.x[[1]])),
        label = paste0(primary_author, " (", year, ")")
      ) %>%
      pull(label)

    events <- round(sept9_data$proportion_positive * sept9_data$sample_size)
    ci_bounds <- prop.test(events, sept9_data$sample_size)$conf.int
    prop_value <- events / sept9_data$sample_size

    plot_data <- tibble(
      study = study_label,
      proportion = prop_value,
      ci_lower = ci_bounds[1],
      ci_upper = ci_bounds[2]
    )

    ggplot(plot_data, aes(x = study, y = proportion)) +
      geom_pointrange(aes(ymin = ci_lower, ymax = ci_upper), size = 0.6, color = "#1b6ca8") +
      geom_hline(yintercept = plot_data$proportion[1], linetype = "dashed", color = "#999999") +
      coord_flip(clip = "off") +
      scale_y_continuous(labels = scales::percent_format(accuracy = 1)) +
      labs(
        title = "SEPT9 Positivity Rate",
        subtitle = sprintf(
          "%s: %s%% (95%% CI %s to %s)",
          plot_data$study[1],
          scales::percent(plot_data$proportion[1], accuracy = 0.1),
          scales::percent(plot_data$ci_lower[1], accuracy = 0.1),
          scales::percent(plot_data$ci_upper[1], accuracy = 0.1)
        ),
        x = "",
        y = "Proportion positive"
      ) +
      theme_minimal(base_size = 12) +
      theme(
        plot.margin = grid::unit(c(1, 2, 1, 1.5), "cm"),
        axis.text.x = element_text(hjust = 0.5),
        panel.grid.major.y = element_blank(),
        panel.grid.minor = element_blank()
      )

    ggsave("figures/Figure2_ForestPlot_mSEPT9.png", width = 9, height = 4.5, dpi = 300)
  }

  # Figure 3: Conceptual Model (simplified boxplot)
  cat("Creating conceptual model visualization...\n")

  ggplot(data, aes(x = exposure_type, y = epigenetic_effect_size)) +
    geom_boxplot(fill = "lightblue", alpha = 0.7) +
    geom_jitter(width = 0.2, alpha = 0.6) +
    theme_minimal() +
    labs(title = "Epigenetic Effects by Exposure Domain",
         x = "Exposure Type",
         y = "Effect Size") +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))

  ggsave("figures/Figure3_Conceptual_Model.png", width = 8, height = 6, dpi = 300)

  # ===============================================
  # 4. Generate Tables
  # ===============================================

  # Table 1: Environmental Signatures
  cat("Creating environmental signatures table...\n")

  env_data <- data %>% filter(exposure_type == "environmental")
  write_csv(env_data %>% select(authors, year, epigenetic_marker, epigenetic_effect_size, population_size, country, pmid), "output/Table1_Environmental_Signatures.csv")

  # Table 2: Nutritional and Behavioural
  cat("Creating nutritional/behavioural table...\n")

  nut_behav_data <- data %>% filter(exposure_type %in% c("nutritional", "behavioural"))
  write_csv(nut_behav_data %>% select(authors, year, exposure_type, epigenetic_marker, epigenetic_effect_size, population_size, country, pmid), "output/Table2_Nutritional_Behavioural.csv")

  # Additional Visualizations
  if (nrow(nma_data) > 0) {
    cat("Creating network visualizations...\n")

    # Funnel-style scatter of mean effect vs standard error
    funnel_data <- nma_data %>%
      mutate(direction = case_when(
        mean_effect >= 0 ~ "Positive",
        TRUE ~ "Negative"
      ))

    ggplot(funnel_data, aes(x = mean_effect, y = se_effect, color = direction, label = exposure_type)) +
      geom_point(size = 3) +
      geom_text(vjust = -1, size = 3) +
      scale_y_reverse() +
      labs(
        title = "Exposure-Level Precision Plot",
        x = "Mean standardized effect",
        y = "Standard error (inverted)",
        color = "Effect direction"
      ) +
      theme_minimal()

    ggsave("figures/Figure4_Exposure_Funnel.png", width = 8, height = 6, dpi = 300)

    # Network map
    angles <- seq(0, 2 * pi, length.out = nrow(nma_data) + 1)[1:nrow(nma_data)]
    network_nodes <- nma_data %>%
      mutate(
        angle = angles,
        x = cos(angle),
        y = sin(angle)
      )

    if (nrow(comparison_df) > 0) {
      comparison_df_full <- dplyr::bind_rows(
        comparison_df,
        comparison_df %>%
          transmute(
            exposure_a = exposure_b,
            exposure_b = exposure_a,
            mean_difference = -mean_difference,
            ci_lower = -ci_upper,
            ci_upper = -ci_lower,
            p_value = p_value
          )
      )

      network_edges <- comparison_df_full %>%
        mutate(
          weight = abs(mean_difference),
          direction = if_else(mean_difference >= 0, "A higher", "B higher")
        ) %>%
        left_join(network_nodes %>% select(exposure_a = exposure_type, x_start = x, y_start = y), by = "exposure_a") %>%
        left_join(network_nodes %>% select(exposure_b = exposure_type, x_end = x, y_end = y), by = "exposure_b")
        network_edges <- network_edges %>%
          filter(
            !is.na(x_start),
            !is.na(x_end),
            !(abs(x_start - x_end) < 1e-6 & abs(y_start - y_end) < 1e-6)
          )

      if (nrow(network_edges) > 0) {
        ggplot(network_edges) +
        geom_curve(aes(
          x = x_start, y = y_start, xend = x_end, yend = y_end,
          linewidth = weight, color = direction
        ),
        curvature = 0.2, alpha = 0.7
        ) +
        geom_point(data = network_nodes, aes(x = x, y = y, size = mean_effect, color = exposure_type), show.legend = FALSE) +
        geom_text(data = network_nodes, aes(x = x, y = y, label = exposure_type), vjust = -1) +
        scale_size_continuous(range = c(0.3, 2.5), guide = "none") +
        labs(
          title = "Network of Exposure Comparisons",
          color = "",
          linewidth = "Absolute MD"
        ) +
        theme_void()

        ggsave("figures/Figure5_Exposure_Network.png", width = 6, height = 6, dpi = 300)
      }

      # Heatmap of pairwise differences
      heatmap_data <- comparison_df_full %>%
        mutate(
          label = sprintf("%.2f\n(%.2f, %.2f)", mean_difference, ci_lower, ci_upper)
        )

      exposures_order <- unique(c(nma_data$exposure_type))
      heatmap_matrix <- expand_grid(
        exposure_a = exposures_order,
        exposure_b = exposures_order
      ) %>%
        left_join(comparison_df_full, by = c("exposure_a", "exposure_b")) %>%
        mutate(
          mean_difference = if_else(exposure_a == exposure_b, 0, mean_difference),
          label = if_else(exposure_a == exposure_b, "0", sprintf("%.2f", mean_difference)),
          direction = case_when(
            exposure_a == exposure_b ~ "Reference",
            mean_difference > 0 ~ "A higher",
            mean_difference < 0 ~ "B higher",
            TRUE ~ "Reference"
          )
        )

      ggplot(heatmap_matrix, aes(x = exposure_b, y = exposure_a, fill = mean_difference)) +
        geom_tile(color = "white") +
        geom_text(aes(label = label), size = 3) +
        scale_fill_gradient2(
          low = "#4575b4", mid = "#ffffbf", high = "#d73027",
          midpoint = 0,
          name = "MD"
        ) +
        labs(
          title = "Pairwise Mean Differences Between Exposure Types",
          x = "Comparator",
          y = "Reference"
        ) +
        theme_minimal() +
        theme(axis.text.x = element_text(angle = 45, hjust = 1))

      ggsave("figures/Figure6_Exposure_Heatmap.png", width = 8, height = 6, dpi = 300)
    }
  }

} else {
  cat("No SEPT9 data available for meta-analysis\n")
}

# ===============================================
# 5. Session Log
# ===============================================

cat("Appending to session log...\n")
session_info <- capture.output(sessionInfo())
write(session_info, file = "output/session_log.txt", append = TRUE)

cat("Meta-analysis completed successfully\n")
