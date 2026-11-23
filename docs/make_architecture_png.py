"""
Script to generate high-resolution SmartMIS system architecture diagram.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_architecture_diagram(output_path: str = "docs/architecture.png"):
    fig, ax = plt.subplots(figsize=(16, 11), dpi=250)
    fig.patch.set_facecolor("#0F172A") # Deep Navy / Slate background
    ax.set_facecolor("#0F172A")

    # Title & Subtitle
    ax.text(8.0, 10.4, "SmartMIS: Automated Manufacturing Intelligence & MIS Architecture",
            fontsize=20, weight="bold", color="#F8FAFC", ha="center")
    ax.text(8.0, 10.05, "Sakthi Hackathon 2.0 | PS-005: Automated Manufacturing MIS & Rejection Report Generator | Team firstones",
            fontsize=11, color="#94A3B8", ha="center")

    # Helper function for drawing styled layer boxes
    def draw_layer_card(x, y, w, h, title, subtitle, bg_color, border_color):
        box = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.15,rounding_size=0.15",
            facecolor=bg_color, edgecolor=border_color, linewidth=1.8
        )
        ax.add_patch(box)
        ax.text(x + 0.3, y + h - 0.35, title, fontsize=12, weight="bold", color="#F1F5F9")
        ax.text(x + 0.3, y + h - 0.65, subtitle, fontsize=8.5, style="italic", color="#94A3B8")

    def draw_sub_component(x, y, w, h, title, desc, tag_color):
        c_box = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.08",
            facecolor="#1E293B", edgecolor="#334155", linewidth=1.2
        )
        ax.add_patch(c_box)
        # Accent tag
        tag = patches.Rectangle((x, y + h - 0.08), w, 0.08, facecolor=tag_color)
        ax.add_patch(tag)
        ax.text(x + w/2, y + h - 0.35, title, fontsize=9.5, weight="bold", color="#E2E8F0", ha="center")
        ax.text(x + w/2, y + 0.22, desc, fontsize=7.5, color="#94A3B8", ha="center")

    # -------------------------------------------------------------
    # Layer 1: Ingestion & Telemetry (Bottom)
    # -------------------------------------------------------------
    draw_layer_card(0.8, 0.6, 14.4, 1.6, "1. HETEROGENEOUS INGESTION & DATA CONNECTIVITY",
                    "Multi-source shopfloor PMS collectors, live APIs, and column normalization", "#131E35", "#3B82F6")
    draw_sub_component(1.2, 0.8, 3.2, 0.85, "Shopfloor Files", "CSV / Excel Multi-Encoding", "#3B82F6")
    draw_sub_component(4.7, 0.8, 3.2, 0.85, "SQLAlchemy Gateway", "MySQL, MSSQL, SQLite", "#60A5FA")
    draw_sub_component(8.2, 0.8, 3.2, 0.85, "FastAPI Mock PMS", "REST Streaming Endpoint", "#06B6D4")
    draw_sub_component(11.7, 0.8, 3.1, 0.85, "Column Mapping Studio", "Fuzzy Mapping & Presets", "#38BDF8")

    # -------------------------------------------------------------
    # Layer 2: ETL & Persistence Layer
    # -------------------------------------------------------------
    draw_layer_card(0.8, 2.5, 14.4, 1.6, "2. INCREMENTAL ETL & CENTRAL PERSISTENCE",
                    "Idempotent data pipeline, deduplication, and regulatory security audit storage", "#131E35", "#10B981")
    draw_sub_component(1.2, 2.7, 4.4, 0.85, "Composite Idempotent Loader", "Duplicate detection via natural key", "#10B981")
    draw_sub_component(5.9, 2.7, 4.3, 0.85, "Central SQLite Store", "pms_data & ingestion_log tables", "#34D399")
    draw_sub_component(10.5, 2.7, 4.3, 0.85, "Security Audit Trail", "action_audit_log (RBAC tracking)", "#059669")

    # -------------------------------------------------------------
    # Layer 3: Manufacturing Intelligence & Quality Analytics Core
    # -------------------------------------------------------------
    draw_layer_card(0.8, 4.4, 14.4, 1.8, "3. MANUFACTURING INTELLIGENCE & QUALITY ANALYTICS CORE",
                    "Autonomous statistical quality engineering, OEE, financial costing, and forecasting", "#131E35", "#F59E0B")
    draw_sub_component(1.1, 4.6, 2.6, 1.05, "OEE & Plant KPIs", "Availability x Perf x Qual\nFPY, PPM, Plan Adherence", "#F59E0B")
    draw_sub_component(3.9, 4.6, 2.6, 1.05, "Cost of Poor Quality", "Scrap & Rework ₹ Matrix\nTop 5 Financial Loss Drivers", "#FBBF24")
    draw_sub_component(6.7, 4.6, 2.6, 1.05, "SPC p-Chart Studio", "Dynamic 3σ UCL / LCL\nWestern Electric Rules 1-3", "#F59E0B")
    draw_sub_component(9.5, 4.6, 2.6, 1.05, "MAD Anomaly Alerts", "Rolling Median Z-Score\nCRITICAL / WARNING Tiers", "#D97706")
    draw_sub_component(12.3, 4.6, 2.6, 1.05, "14-Day Forecasting", "Statsmodels Holt-Winters\n95% Confidence Intervals", "#B45309")

    # -------------------------------------------------------------
    # Layer 4: AI & Executive Decision Layer
    # -------------------------------------------------------------
    draw_layer_card(0.8, 6.5, 14.4, 1.6, "4. AI CONVERSATIONAL QUERY & EXECUTIVE DECISION ENGINE",
                    "Whitelisted natural-language analytics, automated root-cause diagnostics, and GM briefing", "#131E35", "#8B5CF6")
    draw_sub_component(1.2, 6.7, 4.4, 0.85, "'Ask Your Data' Safe NLP", "Whitelisted [top_n, trend, compare, kpi]\nClaude API + Rule-Based Fallback", "#8B5CF6")
    draw_sub_component(5.9, 6.7, 4.3, 0.85, "Smart Insights Engine", "3 Critical Quantitative Findings\n3 Prioritized Engineering Actions", "#A78BFA")
    draw_sub_component(10.5, 6.7, 4.3, 0.85, "Role-Based Access Control", "Admin, Manager, Operator\nDepartmental Data Scoping", "#7C3AED")

    # -------------------------------------------------------------
    # Layer 5: Presentation & Ecosystem Delivery (Top)
    # -------------------------------------------------------------
    draw_layer_card(0.8, 8.4, 14.4, 1.6, "5. MULTI-CHANNEL PRESENTATION & ECOSYSTEM EXPORT",
                    "Interactive dashboards, approved YAML document generators, Power BI star-schema, and cron email", "#131E35", "#EC4899")
    draw_sub_component(1.1, 8.6, 2.6, 0.85, "Streamlit Portal", "16 Responsive Modules\nLive Spike & ROI Calc", "#EC4899")
    draw_sub_component(3.9, 8.6, 2.6, 0.85, "YAML Report Engine", "Weekly Foundry & Machining\nMonthly Rejection Templates", "#F472B6")
    draw_sub_component(6.7, 8.6, 2.6, 0.85, "Excel & PDF Generators", "A4 Landscape Native Charts\nSign-off Approval Blocks", "#DB2777")
    draw_sub_component(9.5, 8.6, 2.6, 0.85, "Power BI Star Schema", "Clean CSV + DAX Measures\nExecutive Presentation Ready", "#BE185D")
    draw_sub_component(12.3, 8.6, 2.6, 0.85, "Automated Cron & SMTP", "Dynamic UI Schedule\nMulti-attachment Delivery", "#9D174D")

    # Connecting Flow Arrows
    for y_pos in [2.35, 4.25, 6.35, 8.25]:
        ax.annotate(
            "", xy=(8.0, y_pos + 0.15), xytext=(8.0, y_pos - 0.15),
            arrowprops=dict(arrowstyle="->", color="#38BDF8", lw=2.5, mutation_scale=15)
        )

    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11)
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(output_path, dpi=250, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Architecture diagram generated successfully at: {output_path}")

if __name__ == "__main__":
    generate_architecture_diagram()
