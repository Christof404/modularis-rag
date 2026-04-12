import matplotlib.pyplot as plt
from pathlib import Path

class MetricVisualizer:
    """
    Service for creating high-quality visualizations of evaluation results.
    """

    @staticmethod
    def create_scaling_plot(all_summaries: list, save_path: str | Path, title: str = None):
        """
        Creates a line plot showing the development of all metrics over num_samples.
        """
        if not all_summaries:
            return

        # ... (Prepare Data)
        sorted_summaries = sorted(all_summaries, key=lambda x: x.get("num_samples", 0))
        x_values = [s["num_samples"] for s in sorted_summaries]

        sample_s = sorted_summaries[0]
        ks = [1, 3, 5, 10]
        metrics = sample_s.get("available_metrics", ["recall"])

        plot_keys = []
        for m in metrics:
            for k in ks:
                key = f"{m}@{k}"
                if key in sample_s:
                    plot_keys.append(key)

        # 2. Plotting
        plt.figure(figsize=(12, 7), dpi=300)
        colormap = plt.cm.get_cmap('tab20', len(plot_keys))

        for i, key in enumerate(plot_keys):
            y_values = [s.get(key, 0) for s in sorted_summaries]
            plt.plot(x_values, y_values, marker='o', linestyle='-', linewidth=2, 
                     label=key.replace("_", " ").title(), color=colormap(i))

        if "global_recall" in sample_s:
            global_recalls = [s.get("global_recall", 0) for s in sorted_summaries]
            plt.plot(x_values, global_recalls, marker='x', linestyle='--', color='black', 
                     linewidth=1.5, label="Global Recall", alpha=0.7)

        # 3. Styling
        plt.title(title or "RAG Scaling Analysis: Performance vs. Database Size", fontsize=14, pad=20)
        plt.xlabel("Number of Samples (Documents)", fontsize=12)

        plt.ylabel("Metric Score (0.0 - 1.0)", fontsize=12)
        plt.ylim(-0.02, 1.05)
        plt.grid(True, linestyle='--', alpha=0.6)
        
        # Put legend outside to the right
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0., fontsize=10)
        
        plt.tight_layout()
        
        # 4. Save
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
