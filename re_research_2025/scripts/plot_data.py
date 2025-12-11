import matplotlib.pyplot as plt
import csv
import os

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, "../data/extracted_data.csv")
    output_dir = os.path.join(script_dir, "../assets")
    os.makedirs(output_dir, exist_ok=True)
    
    interventions = {}
    cancers = {}
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            i = row["Intervention"]
            c = row["Cancer Type"]
            interventions[i] = interventions.get(i, 0) + 1
            cancers[c] = cancers.get(c, 0) + 1
            
    # Plot 1: Interventions (Pie Chart)
    plt.figure(figsize=(10, 6))
    labels = [f"{k} ({v})" for k, v in interventions.items()]
    sizes = list(interventions.values())
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=plt.cm.Pastel1.colors)
    plt.title("Distribution of Intervention Types in Epigenetics Research (2024-2025)")
    plt.axis('equal')
    plt.savefig(os.path.join(output_dir, "Figure_1_Interventions.png"))
    print("Saved Figure_1_Interventions.png")
    
    # Plot 2: Cancer Types (Bar Chart)
    plt.figure(figsize=(10, 6))
    # Sort by count
    sorted_cancers = sorted(cancers.items(), key=lambda x: x[1], reverse=True)
    keys = [x[0] for x in sorted_cancers]
    vals = [x[1] for x in sorted_cancers]
    
    plt.bar(keys, vals, color='skyblue')
    plt.title("Frequency of Cancer Types Investigated")
    plt.xlabel("Cancer Type")
    plt.ylabel("Number of Studies")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "Figure_2_Cancer_Types.png"))
    print("Saved Figure_2_Cancer_Types.png")

if __name__ == "__main__":
    main()
