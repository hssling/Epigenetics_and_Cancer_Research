import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_dag():
    fig, ax = plt.figure(figsize=(12, 8)), plt.gca()
    ax.axis('off')
    
    # Define box properties
    box_props = dict(boxstyle="round,pad=0.5", fc="white", ec="black", lw=2)
    highlight_props = dict(boxstyle="round,pad=0.5", fc="#e6f3ff", ec="#0066cc", lw=2) # Light blue
    outcome_props = dict(boxstyle="round,pad=0.5", fc="#e6ffe6", ec="#00cc00", lw=2) # Light green
    bad_outcome_props = dict(boxstyle="round,pad=0.5", fc="#ffe6e6", ec="#cc0000", lw=2) # Light red

    # Coordinates (0-1 scale)
    # Level 1: Input
    ax.text(0.5, 0.9, "Lifestyle & Environment\n(Exposome)", ha="center", va="center", size=14, bbox=box_props)
    
    # Level 2: Modifiers
    ax.text(0.5, 0.75, "Epigenetic Modifiers", ha="center", va="center", size=14, bbox=highlight_props)
    
    # Level 3: Specific Inputs
    ax.text(0.2, 0.6, "Dietary Phytochemicals\n(e.g., Curcumin, Sulforaphane)", ha="center", va="center", size=10, bbox=box_props)
    ax.text(0.5, 0.6, "Physical Activity\n(Gut-Muscle Axis)", ha="center", va="center", size=10, bbox=box_props)
    ax.text(0.8, 0.6, "Toxins / Oncogenic Infections\n(Stress / Pollution)", ha="center", va="center", size=10, bbox=box_props)
    
    # Level 4: Molecular Mechanisms
    ax.text(0.35, 0.4, "DNMT Inhibition\n(Demethylation)", ha="center", va="center", size=10, bbox=box_props)
    ax.text(0.35, 0.3, "HDAC Inhibition\n(Chromatin Opening)", ha="center", va="center", size=10, bbox=box_props)
    
    ax.text(0.8, 0.35, "Promoter Hypermethylation\n(Gene Silencing)", ha="center", va="center", size=10, bbox=box_props)
    
    # Level 5: Outcomes
    ax.text(0.35, 0.15, "Re-activation of Tumor Suppressors\n(e.g., GSTP1, PTEN, NRF2)", ha="center", va="center", size=12, bbox=outcome_props)
    ax.text(0.35, 0.05, "Cancer Prevention / Cell Cycle Arrest", ha="center", va="center", size=12, bbox=outcome_props)
    
    ax.text(0.8, 0.15, "Silencing of Tumor Suppressors", ha="center", va="center", size=12, bbox=bad_outcome_props)
    ax.text(0.8, 0.05, "Carcinogenesis / Progression", ha="center", va="center", size=12, bbox=bad_outcome_props)

    # Arrows
    arrow_props = dict(arrowstyle="->", lw=1.5, color="black")
    
    # L1 -> L2
    ax.annotate("", xy=(0.5, 0.79), xytext=(0.5, 0.86), arrowprops=arrow_props)
    
    # L2 -> L3
    ax.annotate("", xy=(0.2, 0.64), xytext=(0.45, 0.71), arrowprops=arrow_props)
    ax.annotate("", xy=(0.5, 0.64), xytext=(0.5, 0.71), arrowprops=arrow_props)
    ax.annotate("", xy=(0.8, 0.64), xytext=(0.55, 0.71), arrowprops=arrow_props)
    
    # L3 -> L4 (Good paths)
    ax.annotate("", xy=(0.3, 0.44), xytext=(0.2, 0.56), arrowprops=arrow_props) # Phytochems to DNMT
    ax.annotate("", xy=(0.4, 0.44), xytext=(0.5, 0.56), arrowprops=arrow_props) # Phys Act to DNMT/HDAC (simplified)
    # L3 -> L4 (Bad paths)
    ax.annotate("", xy=(0.8, 0.39), xytext=(0.8, 0.56), arrowprops=arrow_props)
    
    # L4 -> L5 (Outcomes) - Link DNMT/HDAC to Re-activation
    ax.annotate("", xy=(0.35, 0.19), xytext=(0.35, 0.26), arrowprops=arrow_props) # from mid point of mech
    
    # Link Re-activation to Prevention
    ax.annotate("", xy=(0.35, 0.09), xytext=(0.35, 0.11), arrowprops=arrow_props)
    
    # Link Bad Path
    ax.annotate("", xy=(0.8, 0.19), xytext=(0.8, 0.31), arrowprops=arrow_props)
    ax.annotate("", xy=(0.8, 0.09), xytext=(0.8, 0.11), arrowprops=arrow_props)
    
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "../assets")
    os.makedirs(output_dir, exist_ok=True)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, "Figure_3_DAG.png")
    plt.savefig(output_path, dpi=300)
    print(f"Saved Figure_3_DAG.png to {output_path}")

if __name__ == "__main__":
    draw_dag()
