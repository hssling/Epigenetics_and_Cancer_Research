import subprocess
import os
import sys

def run_script(script_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    
    print(f"=== Running {script_name} ===")
    try:
        # Run script using the current python executable
        result = subprocess.run([sys.executable, script_path], check=True, cwd=script_dir)
        print(f"=== {script_name} completed successfully ===\n")
    except subprocess.CalledProcessError as e:
        print(f"!!! Error running {script_name}. Exit code: {e.returncode} !!!")
        sys.exit(1)

def main():
    print("Starting Epigenetics Research Pipeline (2025)...")
    
    # 1. Fetch Data
    run_script("fetch_data.py")
    
    # 2. Analyze & Extract
    run_script("analyze_data.py")
    
    # 3. Visualization
    run_script("plot_data.py")
    run_script("draw_dag.py")
    
    # 4. Doc Generation
    run_script("generate_manuscript_docx.py")
    run_script("generate_icmr_docs.py")
    
    print("Pipeline completed successfully! All artifacts generated.")

if __name__ == "__main__":
    main()
